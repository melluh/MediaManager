import asyncio
import logging
import re
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID

import media_manager.metadataProvider.utils
from media_manager.common.import_match import (
    ImportMatchConfidence,
    search_result_from_media,
    titles_match,
)
from media_manager.common.import_sidecar import (
    ImportMatchSidecar,
    read_import_sidecar,
    write_import_sidecar,
)
from media_manager.common.media_files import media_directory_name
from media_manager.common.repository import BaseRepository
from media_manager.common.schemas import CURRENT_METADATA_VERSION, BaseMediaFile
from media_manager.common.slug import generate_slug
from media_manager.config import MediaManagerConfig
from media_manager.exceptions import InvalidConfigError, NotFoundError
from media_manager.indexer.service import IndexerService
from media_manager.metadataProvider.abstract_metadata_provider import (
    DEFAULT_SEARCH_MAX_PAGES,
    AbstractMetadataProvider,
)
from media_manager.metadataProvider.schemas import (
    ExternalPosterImage,
    MediaType,
    MetaDataProviderSearchResult,
)
from media_manager.notification.service import NotificationService
from media_manager.schemas import MediaImportSuggestion
from media_manager.torrent.schemas import ImportErrorKind, Torrent, TorrentId
from media_manager.torrent.service import TorrentService
from media_manager.torrent.utils import (
    extract_external_id_from_string,
    get_importable_media_directories,
)

log = logging.getLogger(__name__)

# Each importable directory costs one metadata search, and a scan covers the
# whole media root at once.
_MAX_CONCURRENT_IMPORT_LOOKUPS = 8

# The scan only ever wants the best match, and every extra page is another
# request per directory. Interactive search keeps the provider default.
_IMPORT_SEARCH_MAX_PAGES = 1

# A bracketed or braced group carrying a metadata-provider id, as written by
# this app ("[tmdbid-123]") or by Sonarr/Radarr ("{tmdb-123}"). Only groups
# holding the id are removed, so unrelated tags are left for the search to
# deal with.
_ID_TOKEN_GROUP = re.compile(
    r"\s*[\[{][^\]}]*\b(?:tmdb|tvdb)(?:id)?[-_]?\d+\b[^\]}]*[\]}]",
    re.IGNORECASE,
)

T = TypeVar("T")
S = TypeVar("S")


class BaseMediaService[T, S]:
    """
    Base service providing common logic for media modules.
    """

    def __init__(
        self,
        repository: BaseRepository[T, S],
        torrent_service: TorrentService,
        indexer_service: IndexerService,
        notification_service: NotificationService,
    ) -> None:
        self.repository = repository
        self.torrent_service = torrent_service
        self.indexer_service = indexer_service
        self.notification_service = notification_service

    async def get_all_media(self) -> list[S]:
        return await self.repository.get_all()

    async def attach_media_images(self, media: S) -> S:
        """
        Populates `media.images` based on the image types on disk.
        """
        media.images = await asyncio.to_thread(
            media_manager.metadataProvider.utils.get_available_media_images, media.id
        )
        return media

    async def attach_media_images_many(self, media_list: list[S]) -> list[S]:
        """
        Populates `media.images` based on the image types on disk.
        Batched for multiple media items (more efficient than calling attach_media_images individually).
        """
        if not media_list:
            return media_list
        images_by_id = await asyncio.to_thread(
            media_manager.metadataProvider.utils.get_available_media_images_many,
            [media.id for media in media_list],
        )
        for media in media_list:
            media.images = images_by_id[str(media.id)]
        return media_list

    def get_root_directory(
        self, media: S, default_dir: Path, libraries: list[Any]
    ) -> Path:
        """
        Determines the root directory for a media item.

        Only the parent directory is resolved from the configured libraries;
        the media's own directory name is the one persisted on the row, so
        renaming the media (e.g. on a metadata refresh) never moves the files.
        """
        # Persisted on every stored row, but the schema field is optional
        # because media is built from provider metadata before it is assigned.
        # Recomputing gives exactly what the stored value would have been.
        directory_name = media.directory_name or media_directory_name(
            name=media.name,
            year=media.year,
            metadata_provider=media.metadata_provider,
            external_id=media.external_id,
        )
        if hasattr(media, "library") and media.library:
            for library in libraries:
                if library.name == media.library:
                    return Path(library.path) / directory_name
        return default_dir / directory_name

    async def media_file_is_imported(self, media_file: BaseMediaFile) -> bool:
        """
        Whether a media file is expected to be present on disk, i.e. whether
        the torrent it came from has been imported. Files with no torrent
        (manually imported ones) always count as present.
        """
        if media_file.torrent_id is None:
            return True
        try:
            torrent = await self.torrent_service.get_torrent_by_id(
                torrent_id=TorrentId(media_file.torrent_id)
            )
        # A torrent lookup failure only means we can't confirm the file, not
        # that the media module should fail the whole request.
        except Exception:
            log.warning(
                f"Could not resolve torrent {media_file.torrent_id} for media file",
                exc_info=True,
            )
            return False
        return bool(torrent.imported)

    def get_media_root_path(self, media: S) -> Path:
        """
        To be implemented by subclasses if they have specific directory logic.
        """
        raise NotImplementedError

    async def notify_import_success(self, media_name: str, media_type: str) -> None:
        if self.notification_service:
            await self.notification_service.send_notification_to_all_providers(
                title=f"{media_type.capitalize()} Downloaded",
                message=f"{media_type.capitalize()} {media_name} has been successfully downloaded and imported.",
            )

    async def notify_import_failure(
        self,
        torrent: Torrent,
        media_name: str,
        media_type: str,
        error_msg: str = "",
        import_error_kind: ImportErrorKind | None = None,
    ) -> None:
        """
        Records the failure on the torrent and notifies, but only when the
        stored error actually changes - repeated cron passes over the same
        unresolved failure must not re-notify every run.

        :param import_error_kind: Set when the failure is one the API can offer
            a targeted resolution flow for; left unset otherwise.
        """
        stored_error = error_msg or "Unknown error"
        if self.notification_service and torrent.import_error != stored_error:
            msg = f"Failed to import files for {media_type} {media_name}."
            if error_msg:
                msg += f" Error: {error_msg}"
            await self.notification_service.send_notification_to_all_providers(
                title="Import Failed",
                message=msg,
            )
        torrent.imported = False
        torrent.import_error = stored_error
        torrent.import_error_kind = import_error_kind
        await self.torrent_service.torrent_repository.save_torrent(torrent=torrent)

    async def get_import_candidates(
        self,
        directory: Path,
        metadata_provider: AbstractMetadataProvider,
        search_func: Callable[
            [str, AbstractMetadataProvider, int],
            Awaitable[list[MetaDataProviderSearchResult]],
        ],
    ) -> list[MetaDataProviderSearchResult]:
        """
        Every candidate for one directory, for a user correcting the match the
        scan resolved. Runs the same single-page search the scan runs.

        :param directory: The importable directory to find candidates for.
        :param search_func: The media type's search, taking (query, provider,
            max_pages).
        :return: The search results for the directory's derived title.
        """
        name, _ = self._extract_name_and_year(directory.name)
        return await search_func(name, metadata_provider, _IMPORT_SEARCH_MAX_PAGES)

    async def get_import_suggestion(
        self,
        directory: Path,
        metadata_provider: AbstractMetadataProvider,
        search_func: Callable[
            [str, AbstractMetadataProvider, int],
            Awaitable[list[MetaDataProviderSearchResult]],
        ],
        get_metadata_func: Callable[[int], Awaitable[Any]],
        get_images_func: Callable[
            [int], Awaitable[tuple[list[ExternalPosterImage], list[ExternalPosterImage]]]
        ],
        media_type: MediaType,
    ) -> MediaImportSuggestion:
        """
        The single best match for one importable directory, served from the
        directory's sidecar cache when that is still valid.

        :param directory: The importable directory.
        :param metadata_provider: Provider to resolve the directory against.
        :param search_func: The media type's search, taking (query, provider,
            max_pages).
        :param get_metadata_func: Fetches full metadata by external id, used
            when the directory name carries one.
        :param get_images_func: Fetches poster/backdrop images by external
            id, used alongside `get_metadata_func`.
        :param media_type: Whether the directory holds a movie or a show.
        :return: The suggestion, cached in the directory for the next scan.
        """
        cached = await asyncio.to_thread(read_import_sidecar, directory)
        # The directory name was the input to matching, so a rename has to be
        # re-resolved.
        if cached and cached.directory_name == directory.name:
            return MediaImportSuggestion(
                directory=directory,
                match=cached.match,
                confidence=cached.confidence,
            )

        suggestion = await self._resolve_import_match(
            directory=directory,
            metadata_provider=metadata_provider,
            search_func=search_func,
            get_metadata_func=get_metadata_func,
            get_images_func=get_images_func,
            media_type=media_type,
        )
        # Negative results are cached too: a directory nothing matches is
        # exactly the one that would otherwise be searched for on every scan.
        await asyncio.to_thread(
            write_import_sidecar,
            directory,
            ImportMatchSidecar(
                directory_name=directory.name,
                confidence=suggestion.confidence,
                match=suggestion.match,
            ),
        )
        return suggestion

    async def _resolve_import_match(
        self,
        directory: Path,
        metadata_provider: AbstractMetadataProvider,
        search_func: Callable[
            [str, AbstractMetadataProvider, int],
            Awaitable[list[MetaDataProviderSearchResult]],
        ],
        get_metadata_func: Callable[[int], Awaitable[Any]],
        get_images_func: Callable[
            [int], Awaitable[tuple[list[ExternalPosterImage], list[ExternalPosterImage]]]
        ],
        media_type: MediaType,
    ) -> MediaImportSuggestion:
        """
        Resolves a directory to at most one match, without consulting or
        writing any cache.
        """
        name, year = self._extract_name_and_year(directory.name)
        provider_name, external_id = extract_external_id_from_string(directory.name)

        # An id for the provider in use is worth far more than a search: it is
        # what the directory was named after, and the fetch by id is served
        # from the provider's detail cache.
        if external_id is not None and provider_name == metadata_provider.name:
            match = await self._match_by_external_id(
                external_id=external_id,
                get_metadata_func=get_metadata_func,
                get_images_func=get_images_func,
                media_type=media_type,
            )
            if match is not None:
                return MediaImportSuggestion(
                    directory=directory,
                    match=match,
                    # The id was deliberately written into the directory name,
                    # so a title that disagrees is worth less confidence but
                    # not another round of searching.
                    confidence=ImportMatchConfidence.exact_id
                    if titles_match(name, match.name)
                    else ImportMatchConfidence.best_guess,
                )

        results = await search_func(name, metadata_provider, _IMPORT_SEARCH_MAX_PAGES)
        title_matches = [
            result for result in results if titles_match(name, result.name)
        ]
        if not title_matches:
            return MediaImportSuggestion(
                directory=directory, confidence=ImportMatchConfidence.none
            )

        same_year = next(
            (
                result
                for result in title_matches
                if year is not None and result.year == year
            ),
            None,
        )
        if same_year is not None:
            return MediaImportSuggestion(
                directory=directory,
                match=same_year,
                confidence=ImportMatchConfidence.confident,
            )
        return MediaImportSuggestion(
            directory=directory,
            match=title_matches[0],
            confidence=ImportMatchConfidence.best_guess,
        )

    async def _match_by_external_id(
        self,
        external_id: int,
        get_metadata_func: Callable[[int], Awaitable[Any]],
        get_images_func: Callable[
            [int], Awaitable[tuple[list[ExternalPosterImage], list[ExternalPosterImage]]]
        ],
        media_type: MediaType,
    ) -> MetaDataProviderSearchResult | None:
        """
        The media an id token names, or None when the provider cannot resolve
        it - a stale or mistyped id then falls back to searching.
        """
        try:
            media = await get_metadata_func(external_id)
        except Exception:
            log.debug(
                f"Could not resolve external id {external_id} from directory name",
                exc_info=True,
            )
            return None

        poster_images: list[ExternalPosterImage] = []
        backdrop_images: list[ExternalPosterImage] = []
        try:
            poster_images, backdrop_images = await get_images_func(external_id)
        except Exception:
            # A match is still useful without its poster/backdrop, so this
            # doesn't fall back to searching like a failed metadata fetch does.
            log.debug(
                f"Could not resolve images for external id {external_id}",
                exc_info=True,
            )
        return search_result_from_media(
            media,
            media_type,
            poster_images=poster_images,
            backdrop_images=backdrop_images,
        )

    def _extract_name_and_year(self, directory_name: str) -> tuple[str, int | None]:
        """
        Best-effort title and year for a directory that isn't in the library
        yet, used as the metadata-provider search query. Managed directories
        carry a "[tmdbid-123]" token, which has to come off before the year
        is parsed - otherwise the whole directory name is searched verbatim
        and matches nothing.
        """
        provider, _ = extract_external_id_from_string(directory_name)
        if provider is not None:
            directory_name = _ID_TOKEN_GROUP.sub("", directory_name).strip()
        # Media with no year was once written to disk with a literal "(None)".
        directory_name = directory_name.removesuffix(" (None)").strip()

        match = re.search(r"^(.*)\s\((\d{4})\)$", directory_name)
        if match:
            return match.group(1), int(match.group(2))
        return directory_name, None

    async def get_claimed_directory_names(self) -> set[str]:
        """
        Directory basenames already owned by media of this service's type, so
        that they are never offered for import (nor accepted as an import
        source, which would import a media item's files over themselves).
        """
        return await self.repository.get_all_directory_names()

    async def get_importable_media(
        self,
        root_path: Path,
        metadata_provider: AbstractMetadataProvider,
        get_suggestion_func: Callable[
            [Path, AbstractMetadataProvider], Awaitable[MediaImportSuggestion]
        ],
    ) -> list[MediaImportSuggestion]:
        importable_dirs = get_importable_media_directories(
            root_path, await self.get_claimed_directory_names()
        )
        # A directory whose name carries a provider id for media already in
        # the library needs no lookup at all - it is the same item under a
        # directory name that no longer matches what is stored.
        importable_dirs = [
            directory
            for directory in importable_dirs
            if not await self._is_already_in_library(directory)
        ]

        # One metadata lookup per uncached directory, so the fan-out is as wide
        # as the user's library. Unbounded, that buries the metadata provider (or the
        # relay in front of it) under hundreds of simultaneous requests.
        lookup_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_IMPORT_LOOKUPS)

        async def _suggestion(directory: Path) -> MediaImportSuggestion:
            async with lookup_semaphore:
                return await get_suggestion_func(directory, metadata_provider)

        return list(
            await asyncio.gather(
                *(_suggestion(directory) for directory in importable_dirs)
            )
        )

    async def _is_already_in_library(self, directory: Path) -> bool:
        provider, external_id = extract_external_id_from_string(directory.name)
        if provider is None or external_id is None:
            return False
        return await self.repository.exists_by_external_id(
            external_id=external_id, metadata_provider=provider
        )

    async def import_all_torrents_base(
        self,
        get_media_func: Callable[[Any], Awaitable[S | None]],
        import_torrent_func: Callable[[Any, S], Awaitable[None]],
        media_type_name: str,
    ) -> None:
        log.info(f"Importing all torrents for {media_type_name}")
        start = time.monotonic()
        torrents = await self.torrent_service.get_completed_torrents()
        imported_count = 0
        for t in torrents:
            if t.imported or t.import_error:
                continue
            torrent_start = time.monotonic()
            try:
                media = await get_media_func(t)
                if media:
                    await import_torrent_func(t, media)
                    imported_count += 1
            except Exception:
                log.exception(f"Error importing torrent {t.title}")
            log.info(
                f"Processing torrent '{t.title}' ({media_type_name}) took "
                f"{time.monotonic() - torrent_start:.3f}s"
            )
        log.info(
            f"Finished importing all torrents for {media_type_name}: "
            f"{imported_count}/{len(torrents)} candidate(s) imported in "
            f"{time.monotonic() - start:.3f}s"
        )


class BaseMetadataService[T, S]:
    """
    Base service for metadata operations.
    """

    def __init__(self, repository: BaseRepository[T, S]) -> None:
        self.repository = repository

    async def check_if_exists(self, external_id: int, metadata_provider: str) -> bool:
        return await self.repository.exists_by_external_id(
            external_id=external_id, metadata_provider=metadata_provider
        )

    async def add_media_base(
        self,
        external_id: int,
        metadata_provider: AbstractMetadataProvider,
        media_type: MediaType,
        get_metadata_func: Callable[..., Awaitable[S]],
        save_func: Callable[[S], Awaitable[S]],
        language: str | None = None,
        include_year_in_slug: bool = True,
        added_by_user_id: UUID | None = None,
    ) -> S:
        media_with_metadata = await get_metadata_func(external_id, language=language)
        if not media_with_metadata:
            raise NotFoundError

        media_with_metadata.slug = await generate_slug(
            media_with_metadata.name,
            media_with_metadata.year if include_year_in_slug else None,
            self.repository.slug_exists,
        )
        media_with_metadata.directory_name = media_directory_name(
            name=media_with_metadata.name,
            year=media_with_metadata.year,
            metadata_provider=metadata_provider.name,
            external_id=external_id,
        )
        media_with_metadata.added_by_user_id = added_by_user_id

        saved_media = await save_func(media_with_metadata)
        await metadata_provider.download_all_media_images(saved_media, media_type)
        return saved_media

    async def search_for_media_base(
        self,
        query: str,
        metadata_provider: AbstractMetadataProvider,
        search_func: Callable[..., Awaitable[list[MetaDataProviderSearchResult]]],
        max_pages: int = DEFAULT_SEARCH_MAX_PAGES,
    ) -> list[MetaDataProviderSearchResult]:
        """
        :param max_pages: Pages of provider results to search through. Left at
            the provider default for interactive search; the import scan asks
            for a single page.
        """
        results = await search_func(query, max_pages=max_pages)
        # One query for the whole page of results, rather than an existence
        # check plus a lookup per result.
        added = await self.repository.get_ids_by_external_ids(
            external_ids=[result.external_id for result in results],
            metadata_provider=metadata_provider.name,
        )
        for result in results:
            stored = added.get(result.external_id)
            if stored is None:
                continue
            result.added = True
            result.id, result.slug = stored
        return results

    async def get_popular_media_base(
        self,
        metadata_provider: AbstractMetadataProvider,
        search_func: Callable[
            [str | None], Awaitable[list[MetaDataProviderSearchResult]]
        ],
    ) -> list[MetaDataProviderSearchResult]:
        results = await search_func(None)
        return [
            r
            for r in results
            if not await self.check_if_exists(
                external_id=r.external_id,
                metadata_provider=metadata_provider.name,
            )
        ]

    async def update_all_metadata_base(
        self,
        get_all_to_update_func: Callable[[], Awaitable[list[S]]],
        update_single_func: Callable[
            [S, AbstractMetadataProvider], Awaitable[S | None]
        ],
        tmdb_provider_class: Callable[[], AbstractMetadataProvider],
        tvdb_provider_class: Callable[[], AbstractMetadataProvider],
        media_type_name: str,
    ) -> None:
        log.info(f"Updating metadata for all {media_type_name}")
        media_list = await get_all_to_update_func()

        refetch_interval_hours = MediaManagerConfig().metadata.refetch_interval_hours
        min_age = timedelta(hours=refetch_interval_hours)
        now = datetime.now(UTC)
        media_list = [
            item
            for item in media_list
            if item.metadata_updated_at is None
            or now - item.metadata_updated_at >= min_age
            or item.metadata_version != CURRENT_METADATA_VERSION
        ]

        log.info(f"Found {len(media_list)} {media_type_name} to update")
        for item in media_list:
            try:
                if item.metadata_provider == "tmdb":
                    provider = tmdb_provider_class()
                elif item.metadata_provider == "tvdb":
                    provider = tvdb_provider_class()
                else:
                    log.error(
                        f"Unsupported provider {item.metadata_provider} for {item.name}"
                    )
                    continue
                await update_single_func(item, provider)
            except InvalidConfigError:
                log.exception(f"Config error for {item.name}")
            except Exception:
                log.exception(f"Error updating {item.name}")
