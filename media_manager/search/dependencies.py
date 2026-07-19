from typing import Annotated

from fastapi import Depends

from media_manager.movies.dependencies import movie_repository_dep
from media_manager.search.schemas import MediaType
from media_manager.search.service import SearchService
from media_manager.tv.dependencies import tv_repository_dep


def get_search_service(
    movie_repository: movie_repository_dep,
    tv_repository: tv_repository_dep,
) -> SearchService:
    return SearchService(
        repositories={
            MediaType.movie: movie_repository,
            MediaType.tv: tv_repository,
        }
    )


search_service_dep = Annotated[SearchService, Depends(get_search_service)]
