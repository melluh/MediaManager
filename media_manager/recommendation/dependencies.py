from typing import Annotated

from fastapi import Depends

from media_manager.database import DbSessionDependency
from media_manager.metadataProvider.tmdb import TmdbMetadataProvider
from media_manager.recommendation.repository import RecommendationRepository
from media_manager.recommendation.service import RecommendationService
from media_manager.watch_history.dependencies import watch_history_service_dep


def get_recommendation_repository(
    db_session: DbSessionDependency,
) -> RecommendationRepository:
    return RecommendationRepository(db_session)


recommendation_repository_dep = Annotated[
    RecommendationRepository, Depends(get_recommendation_repository)
]


def get_recommendation_service(
    recommendation_repository: recommendation_repository_dep,
    watch_history_service: watch_history_service_dep,
) -> RecommendationService:
    # Always TMDB, whatever provider library media came from: only TMDB has
    # "people who liked this also liked" data.
    return RecommendationService(
        recommendation_repository, watch_history_service, TmdbMetadataProvider()
    )


recommendation_service_dep = Annotated[
    RecommendationService, Depends(get_recommendation_service)
]
