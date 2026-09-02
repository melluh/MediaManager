from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from media_manager.auth.db import User
from media_manager.auth.users import current_active_user, current_superuser
from media_manager.common.import_scan_cache import (
    ImportScanMediaType,
    get_cached_importable_media,
)
from media_manager.config import LibraryItem, MediaManagerConfig
from media_manager.exceptions import ConflictError, NotFoundError
from media_manager.indexer.schemas import (
    IndexerQueryResult,
    IndexerQueryResultId,
)
from media_manager.metadataProvider.dependencies import metadata_provider_dep
from media_manager.metadataProvider.schemas import MetaDataProviderSearchResult
from media_manager.movies.dependencies import (
    movie_by_slug_dep,
    movie_dep,
    movie_import_service_dep,
    movie_metadata_service_dep,
    movie_service_dep,
)
from media_manager.movies.schemas import (
    Movie,
    PublicMovie,
    PublicMovieFile,
    RichMovieTorrent,
)
from media_manager.schemas import MediaImportSuggestion
from media_manager.torrent.dependencies import torrent_dep
from media_manager.torrent.schemas import Torrent, TorrentImportCandidate
from media_manager.torrent.utils import get_importable_media_directories

router = APIRouter()

# -----------------------------------------------------------------------------
# METADATA & SEARCH
# -----------------------------------------------------------------------------


@router.get(
    "/search",
    dependencies=[Depends(current_active_user)],
)
async def search_for_movie(
    query: str,
    movie_metadata_service: movie_metadata_service_dep,
    metadata_provider: metadata_provider_dep,
) -> list[MetaDataProviderSearchResult]:
    """
    Search for a movie on the configured metadata provider.
    """
    return await movie_metadata_service.search_for_movie(
        query=query, metadata_provider=metadata_provider
    )


@router.get(
    "/recommended",
    dependencies=[Depends(current_active_user)],
)
async def get_popular_movies(
    movie_metadata_service: movie_metadata_service_dep,
    metadata_provider: metadata_provider_dep,
) -> list[MetaDataProviderSearchResult]:
    """
    Get a list of recommended/popular movies from the metadata provider.
    """
    return await movie_metadata_service.get_popular_movies(
        metadata_provider=metadata_provider
    )


@router.get(
    "/external/{movie_id}",
    dependencies=[Depends(current_active_user)],
)
async def get_external_movie_details(
    movie_metadata_service: movie_metadata_service_dep,
    metadata_provider: metadata_provider_dep,
    movie_id: int,
    language: str | None = None,
) -> Movie:
    """
    Get full details for a movie from the metadata provider, without adding it to the library.
    """
    return await movie_metadata_service.get_movie_details(
        external_id=movie_id,
        metadata_provider=metadata_provider,
        language=language,
    )


@router.get(
    "/external/{movie_id}/torrents",
    dependencies=[Depends(current_active_user)],
)
async def search_for_torrents_for_external_movie(
    movie_service: movie_service_dep,
    movie_metadata_service: movie_metadata_service_dep,
    metadata_provider: metadata_provider_dep,
    movie_id: int,
    language: str | None = None,
) -> list[IndexerQueryResult]:
    """
    Search for torrents for a movie that hasn't been added to the library yet.
    """
    movie = await movie_metadata_service.get_movie_details(
        external_id=movie_id,
        metadata_provider=metadata_provider,
        language=language,
    )
    return await movie_service.get_all_available_torrents_for_movie(movie=movie)


# -----------------------------------------------------------------------------
# IMPORTING
# -----------------------------------------------------------------------------


@router.get(
    "/importable",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(current_superuser)],
)
async def get_all_importable_movies() -> list[MediaImportSuggestion]:
    """
    Get the last-scanned list of unknown movies detected in the movie
    directory that are importable. Backed by a periodically refreshed cache;
    use POST /importable/rescan to force an immediate re-scan.
    """
    return get_cached_importable_media(ImportScanMediaType.movie)


@router.post(
    "/importable/rescan",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(current_superuser)],
)
async def rescan_importable_movies(
    movie_import_service: movie_import_service_dep,
) -> list[MediaImportSuggestion]:
    """
    Immediately re-scans the movie directory for importable movies and
    refreshes the cache used by GET /importable.
    """
    return await movie_import_service.rescan_importable_movies()


@router.post(
    "/importable/{movie_id}",
    dependencies=[Depends(current_superuser)],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def import_detected_movie(
    movie_import_service: movie_import_service_dep, movie: movie_dep, directory: str
) -> None:
    """
    Import a detected movie from the specified directory into the library.
    """
    source_directory = Path(directory)
    if source_directory not in get_importable_media_directories(
        MediaManagerConfig().misc.movie_directory
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No such directory")
    success = await movie_import_service.import_existing_movie(
        movie=movie, source_directory=source_directory
    )
    if not success:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Error on importing")


# -----------------------------------------------------------------------------
# MOVIES
# -----------------------------------------------------------------------------


@router.get(
    "",
    dependencies=[Depends(current_active_user)],
)
async def get_all_movies(movie_service: movie_service_dep) -> list[Movie]:
    """
    Get all movies in the library.
    """
    return await movie_service.get_all_movies()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(current_active_user)],
    responses={
        status.HTTP_201_CREATED: {
            "model": Movie,
            "description": "Successfully created movie",
        }
    },
)
async def add_a_movie(
    movie_metadata_service: movie_metadata_service_dep,
    metadata_provider: metadata_provider_dep,
    movie_id: int,
    language: str | None = None,
) -> Movie:
    """
    Add a new movie to the library.
    """
    try:
        movie = await movie_metadata_service.add_movie(
            external_id=movie_id,
            metadata_provider=metadata_provider,
            language=language,
        )
    except ConflictError:
        movie = await movie_metadata_service.movie_repository.get_movie_by_external_id(
            external_id=movie_id, metadata_provider=metadata_provider.name
        )
        if not movie:
            raise NotFoundError from ConflictError
    return movie


@router.get(
    "/torrents",
    dependencies=[Depends(current_active_user)],
)
async def get_all_movies_with_torrents(
    movie_service: movie_service_dep,
) -> list[RichMovieTorrent]:
    """
    Get all movies that are associated with torrents.
    """
    return await movie_service.get_all_movies_with_torrents()


@router.get(
    "/libraries",
    dependencies=[Depends(current_active_user)],
)
def get_available_libraries() -> list[LibraryItem]:
    """
    Get available Movie libraries from configuration.
    """
    return MediaManagerConfig().misc.movie_libraries


# -----------------------------------------------------------------------------
# MOVIES - SINGLE RESOURCE
# -----------------------------------------------------------------------------


@router.get(
    "/slug/{slug}",
    dependencies=[Depends(current_active_user)],
)
async def get_movie_by_slug(
    movie_service: movie_service_dep, movie: movie_by_slug_dep
) -> PublicMovie:
    """
    Get details for a specific movie by its slug.
    """
    return await movie_service.get_public_movie_by_id(movie=movie)


@router.get(
    "/{movie_id}",
    dependencies=[Depends(current_active_user)],
)
async def get_movie_by_id(
    movie_service: movie_service_dep, movie: movie_dep
) -> PublicMovie:
    """
    Get details for a specific movie.
    """
    return await movie_service.get_public_movie_by_id(movie=movie)


@router.delete(
    "/{movie_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(current_superuser)],
)
async def delete_a_movie(
    movie_service: movie_service_dep,
    movie: movie_dep,
    delete_files_on_disk: bool = False,
    delete_torrents: bool = False,
) -> None:
    """
    Delete a movie from the library.
    """
    await movie_service.delete_movie(
        movie=movie,
        delete_files_on_disk=delete_files_on_disk,
        delete_torrents=delete_torrents,
    )


@router.post(
    "/{movie_id}/library",
    dependencies=[Depends(current_superuser)],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def set_library(
    movie: movie_dep,
    movie_service: movie_service_dep,
    library: str,
) -> None:
    """
    Set the library path for a Movie.
    """
    await movie_service.set_movie_library(movie=movie, library=library)


@router.get(
    "/{movie_id}/files",
    dependencies=[Depends(current_active_user)],
)
async def get_movie_files_by_movie_id(
    movie_service: movie_service_dep, movie: movie_dep
) -> list[PublicMovieFile]:
    """
    Get files associated with a specific movie.
    """
    return await movie_service.get_public_movie_files(movie=movie)


@router.get(
    "/{movie_id}/torrents",
    dependencies=[Depends(current_active_user)],
)
async def search_for_torrents_for_movie(
    movie_service: movie_service_dep,
    movie: movie_dep,
    search_query_override: str | None = None,
    allow_language_variants: list[str] | None = None,
) -> list[IndexerQueryResult]:
    """
    Search for torrents for a specific movie.
    """
    return await movie_service.get_all_available_torrents_for_movie(
        movie=movie,
        search_query_override=search_query_override,
        allow_language_variants=allow_language_variants,
    )


@router.post(
    "/{movie_id}/torrents",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(current_active_user)],
)
async def download_torrent_for_movie(
    movie_service: movie_service_dep,
    movie: movie_dep,
    user: Annotated[User, Depends(current_active_user)],
    public_indexer_result_id: IndexerQueryResultId,
    override_file_path_suffix: str = "",
) -> Torrent:
    """
    Trigger a download for a specific torrent for a movie.
    """
    return await movie_service.download_torrent(
        public_indexer_result_id=public_indexer_result_id,
        movie=movie,
        override_movie_file_path_suffix=override_file_path_suffix,
        user_id=user.id,
    )


async def _get_movie_torrent_or_404(
    movie_import_service: movie_import_service_dep, movie: Movie, torrent: Torrent
) -> None:
    movie_of_torrent = await movie_import_service.torrent_service.get_movie_of_torrent(
        torrent=torrent
    )
    if movie_of_torrent is None or movie_of_torrent.id != movie.id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "This torrent does not belong to this movie"
        )


@router.get(
    "/{movie_id}/torrents/{torrent_id}/import-candidates",
    dependencies=[Depends(current_superuser)],
)
async def get_movie_torrent_import_candidates(
    movie_import_service: movie_import_service_dep,
    movie: movie_dep,
    torrent: torrent_dep,
) -> list[TorrentImportCandidate]:
    """
    Lists the video files found in a torrent's download directory, so a
    torrent whose automatic import failed (e.g. because it contained
    multiple video files) can be resolved manually.
    """
    await _get_movie_torrent_or_404(movie_import_service, movie, torrent)
    return await movie_import_service.torrent_service.get_import_candidates(
        torrent=torrent
    )


@router.post(
    "/{movie_id}/torrents/{torrent_id}/import",
    dependencies=[Depends(current_superuser)],
)
async def resolve_movie_torrent_import(
    movie_import_service: movie_import_service_dep,
    movie: movie_dep,
    torrent: torrent_dep,
    relative_path: str,
) -> Torrent:
    """
    Manually resolves a torrent that failed automatic import (currently:
    the "multiple video files found" failure) by importing the given file,
    identified by its path relative to the torrent's download directory as
    returned by GET .../import-candidates.
    """
    await _get_movie_torrent_or_404(movie_import_service, movie, torrent)
    success = await movie_import_service.resolve_multiple_video_files(
        torrent=torrent, movie=movie, relative_path=relative_path
    )
    if not success:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Error on importing")
    # `torrent` was mutated in place by the successful import - return it
    # directly rather than re-fetching, which would round-trip the download
    # client and could fail even though the import itself already succeeded.
    return torrent
