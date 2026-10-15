from typing import Annotated

from fastapi import Depends

from media_manager.database import DbSessionDependency
from media_manager.rating.repository import RatingRepository
from media_manager.rating.service import RatingService


def get_rating_repository(db_session: DbSessionDependency) -> RatingRepository:
    return RatingRepository(db_session)


rating_repository_dep = Annotated[RatingRepository, Depends(get_rating_repository)]


def get_rating_service(rating_repository: rating_repository_dep) -> RatingService:
    return RatingService(rating_repository)


rating_service_dep = Annotated[RatingService, Depends(get_rating_service)]
