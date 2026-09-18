from typing import Annotated

from fastapi import Depends

from media_manager.config import MediaManagerConfig
from media_manager.movies.dependencies import movie_repository_dep
from media_manager.search.schemas import MediaType
from media_manager.titleIndex.service import TitleSuggestionService
from media_manager.tv.dependencies import tv_repository_dep


def get_title_suggestion_service(
    movie_repository: movie_repository_dep,
    tv_repository: tv_repository_dep,
) -> TitleSuggestionService:
    config = MediaManagerConfig()
    return TitleSuggestionService(
        repositories={
            MediaType.movie: movie_repository,
            MediaType.tv: tv_repository,
        },
        directory=config.misc.title_index_directory,
        config=config.title_index,
    )


title_suggestion_service_dep = Annotated[
    TitleSuggestionService, Depends(get_title_suggestion_service)
]
