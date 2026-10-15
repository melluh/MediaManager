from typing import Annotated

from fastapi import APIRouter, Depends

from media_manager.auth.db import User
from media_manager.auth.users import current_active_user
from media_manager.metadataProvider.schemas import MediaType
from media_manager.recommendation.dependencies import recommendation_service_dep
from media_manager.recommendation.schemas import PersonalRecommendation

router = APIRouter()

current_user_dep = Annotated[User, Depends(current_active_user)]


@router.get("/movies")
async def get_recommended_movies(
    recommendation_service: recommendation_service_dep, user: current_user_dep
) -> list[PersonalRecommendation]:
    """
    Movies the current user will probably like, based on what they rated and
    watched, best first.
    """
    return await recommendation_service.get_recommendations(user.id, MediaType.movie)


@router.get("/shows")
async def get_recommended_shows(
    recommendation_service: recommendation_service_dep, user: current_user_dep
) -> list[PersonalRecommendation]:
    """
    Shows the current user will probably like, based on what they rated and
    watched, best first.
    """
    return await recommendation_service.get_recommendations(user.id, MediaType.tv)
