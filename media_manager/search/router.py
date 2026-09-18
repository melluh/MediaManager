from fastapi import APIRouter, Depends

from media_manager.auth.users import current_active_user
from media_manager.metadataProvider.dependencies import metadata_provider_dep
from media_manager.metadataProvider.schemas import MetaDataProviderSearchResult
from media_manager.search.dependencies import search_service_dep
from media_manager.search.schemas import SearchResult
from media_manager.titleIndex.dependencies import title_suggestion_service_dep
from media_manager.titleIndex.schemas import TitleSuggestion

router = APIRouter()


@router.get(
    "",
    dependencies=[Depends(current_active_user)],
)
async def search_media(
    q: str,
    search_service: search_service_dep,
) -> list[SearchResult]:
    """
    Search local media (movies, TV shows, ...) by name.

    Only queries the local database; no external metadata providers are
    contacted.
    """
    query = q.strip()
    if not query:
        return []
    return await search_service.search(query=query)


@router.get(
    "/external",
    dependencies=[Depends(current_active_user)],
)
async def search_external_media(
    q: str,
    search_service: search_service_dep,
    metadata_provider: metadata_provider_dep,
) -> list[MetaDataProviderSearchResult]:
    """
    Search the metadata provider for movies and TV shows together, ranked
    the way the provider itself ranks combined results. Excludes results
    already in the local library.
    """
    query = q.strip()
    if not query:
        return []
    return await search_service.search_external(
        query=query, metadata_provider=metadata_provider
    )


@router.get(
    "/suggest",
    dependencies=[Depends(current_active_user)],
)
async def suggest_titles(
    q: str,
    title_suggestion_service: title_suggestion_service_dep,
) -> list[TitleSuggestion]:
    """
    Fast, typo-tolerant title autocomplete for media not yet in the library,
    sourced from a local index built from TMDB's daily ID export rather than
    a live provider call. Suggestions carry only a title, media type and
    popularity - no poster/year, since the export has neither.
    """
    query = q.strip()
    if not query:
        return []
    return await title_suggestion_service.suggest(query=query)
