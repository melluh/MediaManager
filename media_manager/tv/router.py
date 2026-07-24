from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from media_manager.auth.db import User
from media_manager.auth.users import current_active_user, current_superuser
from media_manager.config import LibraryItem, MediaManagerConfig
from media_manager.exceptions import MediaAlreadyExistsError, NotFoundError
from media_manager.indexer.schemas import (
    IndexerQueryResult,
    IndexerQueryResultId,
)
from media_manager.metadataProvider.dependencies import metadata_provider_dep
from media_manager.metadataProvider.schemas import MetaDataProviderSearchResult
from media_manager.schemas import MediaImportSuggestion
from media_manager.torrent.schemas import Torrent
from media_manager.torrent.utils import get_importable_media_directories
from media_manager.tv.dependencies import (
    season_dep,
    show_dep,
    tv_import_service_dep,
    tv_metadata_service_dep,
    tv_service_dep,
)
from media_manager.tv.schemas import (
    PublicEpisodeFile,
    PublicShow,
    RichShowTorrent,
    Season,
    Show,
    ShowId,
)

router = APIRouter()

# -----------------------------------------------------------------------------
# METADATA & SEARCH
# -----------------------------------------------------------------------------


@router.get(
    "/search",
    dependencies=[Depends(current_active_user)],
)
async def search_metadata_providers_for_a_show(
    tv_metadata_service: tv_metadata_service_dep,
    query: str,
    metadata_provider: metadata_provider_dep,
) -> list[MetaDataProviderSearchResult]:
    """
    Search for a show on the configured metadata provider.
    """
    return await tv_metadata_service.search_for_show(
        query=query, metadata_provider=metadata_provider
    )


@router.get(
    "/recommended",
    dependencies=[Depends(current_active_user)],
)
async def get_recommended_shows(
    tv_metadata_service: tv_metadata_service_dep,
    metadata_provider: metadata_provider_dep,
) -> list[MetaDataProviderSearchResult]:
    """
    Get a list of recommended/popular shows from the metadata provider.
    """
    return await tv_metadata_service.get_popular_shows(
        metadata_provider=metadata_provider
    )


@router.get(
    "/external/{show_id}",
    dependencies=[Depends(current_active_user)],
)
async def get_external_show_details(
    tv_metadata_service: tv_metadata_service_dep,
    metadata_provider: metadata_provider_dep,
    show_id: int,
    language: str | None = None,
) -> Show:
    """
    Get full details for a show from the metadata provider, without adding it to the library.
    """
    return await tv_metadata_service.get_show_details(
        external_id=show_id,
        metadata_provider=metadata_provider,
        language=language,
    )


# -----------------------------------------------------------------------------
# IMPORTING
# -----------------------------------------------------------------------------


@router.get(
    "/importable",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(current_superuser)],
)
async def get_all_importable_shows(
    tv_import_service: tv_import_service_dep, metadata_provider: metadata_provider_dep
) -> list[MediaImportSuggestion]:
    """
    Get a list of unknown shows that were detected in the TV directory and are importable.
    """
    return await tv_import_service.get_importable_tv_shows(
        metadata_provider=metadata_provider
    )


@router.post(
    "/importable/{show_id}",
    dependencies=[Depends(current_superuser)],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def import_detected_show(
    tv_import_service: tv_import_service_dep, tv_show: show_dep, directory: str
) -> None:
    """
    Import a detected show from the specified directory into the library.
    """
    source_directory = Path(directory)
    if source_directory not in get_importable_media_directories(
        MediaManagerConfig().misc.tv_directory
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No such directory")
    await tv_import_service.import_existing_tv_show(
        tv_show=tv_show, source_directory=source_directory
    )


# -----------------------------------------------------------------------------
# SHOWS
# -----------------------------------------------------------------------------


@router.get(
    "/shows",
    dependencies=[Depends(current_active_user)],
)
async def get_all_shows(tv_service: tv_service_dep) -> list[Show]:
    """
    Get all shows in the library.
    """
    return await tv_service.get_all_shows()


@router.post(
    "/shows",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(current_active_user)],
    responses={
        status.HTTP_201_CREATED: {
            "model": Show,
            "description": "Successfully created show",
        }
    },
)
async def add_a_show(
    tv_metadata_service: tv_metadata_service_dep,
    metadata_provider: metadata_provider_dep,
    show_id: int,
    language: str | None = None,
) -> Show:
    """
    Add a new show to the library.
    """
    try:
        show = await tv_metadata_service.add_show(
            external_id=show_id,
            metadata_provider=metadata_provider,
            language=language,
        )
    except MediaAlreadyExistsError:
        show = await tv_metadata_service.tv_repository.get_show_by_external_id(
            show_id, metadata_provider=metadata_provider.name
        )
        if not show:
            raise NotFoundError from MediaAlreadyExistsError
    return show


@router.get(
    "/shows/torrents",
    dependencies=[Depends(current_active_user)],
)
async def get_shows_with_torrents(tv_service: tv_service_dep) -> list[RichShowTorrent]:
    """
    Get all shows that are associated with torrents.
    """
    return await tv_service.get_all_shows_with_torrents()


@router.get(
    "/shows/libraries",
    dependencies=[Depends(current_active_user)],
)
def get_available_libraries() -> list[LibraryItem]:
    """
    Get available TV libraries from configuration.
    """
    return MediaManagerConfig().misc.tv_libraries


# -----------------------------------------------------------------------------
# SHOWS - INDIVIDUAL
# -----------------------------------------------------------------------------


@router.get(
    "/shows/{show_id}",
    dependencies=[Depends(current_active_user)],
)
async def get_a_show(show: show_dep, tv_service: tv_service_dep) -> PublicShow:
    """
    Get details for a specific show.
    """
    return await tv_service.get_public_show_by_id(show=show)


@router.delete(
    "/shows/{show_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(current_superuser)],
)
async def delete_a_show(
    tv_service: tv_service_dep,
    show: show_dep,
    delete_files_on_disk: bool = False,
    delete_torrents: bool = False,
) -> None:
    """
    Delete a show from the library.
    """
    await tv_service.delete_show(
        show=show,
        delete_files_on_disk=delete_files_on_disk,
        delete_torrents=delete_torrents,
    )


@router.post(
    "/shows/{show_id}/metadata",
    dependencies=[Depends(current_active_user)],
)
async def update_shows_metadata(
    show: show_dep,
    tv_metadata_service: tv_metadata_service_dep,
    tv_service: tv_service_dep,
    metadata_provider: metadata_provider_dep,
) -> PublicShow:
    """
    Update a show's metadata from the provider.
    """
    await tv_metadata_service.update_show_metadata(
        db_show=show, metadata_provider=metadata_provider
    )
    return await tv_service.get_public_show_by_id(show=show)


@router.post(
    "/shows/{show_id}/continuousDownload",
    dependencies=[Depends(current_superuser)],
)
async def set_continuous_download(
    show: show_dep, tv_service: tv_service_dep, continuous_download: bool
) -> PublicShow:
    """
    Toggle whether future seasons of a show will be automatically downloaded.
    """
    updated_show = await tv_service.set_show_continuous_download(
        show=show, continuous_download=continuous_download
    )
    return await tv_service.get_public_show_by_id(show=updated_show)


@router.post(
    "/shows/{show_id}/library",
    dependencies=[Depends(current_superuser)],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def set_library(
    show: show_dep,
    tv_service: tv_service_dep,
    library: str,
) -> None:
    """
    Set the library path for a Show.
    """
    await tv_service.set_show_library(show=show, library=library)
    return


@router.get(
    "/shows/{show_id}/torrents",
    dependencies=[Depends(current_active_user)],
)
async def get_a_shows_torrents(
    show: show_dep, tv_service: tv_service_dep
) -> RichShowTorrent:
    """
    Get torrents associated with a specific show.
    """
    return await tv_service.get_torrents_for_show(show=show)


# -----------------------------------------------------------------------------
# SEASONS
# -----------------------------------------------------------------------------


@router.get(
    "/seasons/{season_id}",
    dependencies=[Depends(current_active_user)],
)
async def get_season(season: season_dep) -> Season:
    """
    Get details for a specific season.
    """
    return season


@router.get(
    "/seasons/{season_id}/files",
    dependencies=[Depends(current_active_user)],
)
async def get_episode_files(
    season: season_dep, tv_service: tv_service_dep
) -> list[PublicEpisodeFile]:
    """
    Get episode files associated with a specific season.
    """
    return await tv_service.get_public_episode_files_by_season_id(season=season)


# -----------------------------------------------------------------------------
# TORRENTS
# -----------------------------------------------------------------------------


@router.get(
    "/torrents",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(current_superuser)],
)
async def get_torrents_for_a_season(
    tv_service: tv_service_dep,
    show_id: ShowId,
    season_number: int = 1,
    search_query_override: str | None = None,
) -> list[IndexerQueryResult]:
    """
    Search for torrents for a specific season of a show.
    Default season_number is 1 because it often returns multi-season torrents.
    """
    return await tv_service.get_all_available_torrents_for_a_season(
        season_number=season_number,
        show_id=show_id,
        search_query_override=search_query_override,
    )


@router.post(
    "/torrents",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(current_superuser)],
)
async def download_a_torrent(
    tv_service: tv_service_dep,
    user: Annotated[User, Depends(current_superuser)],
    public_indexer_result_id: IndexerQueryResultId,
    show_id: ShowId,
    override_file_path_suffix: str = "",
) -> Torrent:
    """
    Trigger a download for a specific torrent.
    """
    return await tv_service.download_torrent(
        public_indexer_result_id=public_indexer_result_id,
        show_id=show_id,
        override_show_file_path_suffix=override_file_path_suffix,
        user_id=user.id,
    )


# -----------------------------------------------------------------------------
# STATISTICS
# -----------------------------------------------------------------------------


@router.get(
    "/episodes/count",
    status_code=status.HTTP_200_OK,
    description="Total number of episodes downloaded",
    dependencies=[Depends(current_active_user)],
)
async def get_total_count_of_downloaded_episodes(tv_service: tv_service_dep) -> int:
    """
    Get the total count of downloaded episodes across all shows.
    """
    return await tv_service.get_total_downloaded_episodes_count()
