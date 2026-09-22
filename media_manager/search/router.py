from fastapi import APIRouter, Depends

from media_manager.auth.users import current_active_user
from media_manager.metadataProvider.dependencies import metadata_provider_dep
from media_manager.metadataProvider.schemas import MetaDataProviderSearchResult
from media_manager.search.dependencies import search_service_dep
from media_manager.search.schemas import CombinedSearchResult, SearchResult

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
    contacted. Typo- and abbreviation-tolerant (e.g. "lotr" finds an added
    "The Lord of the Rings") via the same fuzzy/acronym ranking the title
    index uses - see `SearchService`.
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
    "/combined",
    dependencies=[Depends(current_active_user)],
)
async def combined_search_media(
    q: str,
    search_service: search_service_dep,
) -> list[CombinedSearchResult]:
    """
    One ranked list mixing already-in-library media with fast, typo- and
    abbreviation-tolerant suggestions from the local TMDB title index for
    media not yet in the library. In-library results normally rank first,
    but an exceptionally strong not-in-library match can surface above a
    weak in-library one. See `SearchService.combined_search`.
    """
    query = q.strip()
    if not query:
        return []
    return await search_service.combined_search(query=query)
