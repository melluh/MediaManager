from typing import Annotated

from fastapi import APIRouter, Depends, status

from media_manager.auth.db import User
from media_manager.auth.users import current_active_user
from media_manager.movies.dependencies import movie_dep
from media_manager.rating.dependencies import rating_service_dep
from media_manager.rating.schemas import RatingPrompt, SetRating, UserRating
from media_manager.recommendation.service import enqueue_list_refresh
from media_manager.tv.dependencies import show_dep

router = APIRouter()

current_user_dep = Annotated[User, Depends(current_active_user)]


# -----------------------------------------------------------------------------
# PROMPTS
# -----------------------------------------------------------------------------


@router.get("/movies/prompts")
async def get_rating_prompts(
    rating_service: rating_service_dep, user: current_user_dep
) -> list[RatingPrompt]:
    """
    Movies the current user recently watched on the media server but hasn't
    rated or dismissed yet, most recently watched first.
    """
    return await rating_service.get_rating_prompts(user)


@router.post("/movies/{movie_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_rating_prompt(
    rating_service: rating_service_dep, user: current_user_dep, movie: movie_dep
) -> None:
    """
    Stop asking the current user whether they enjoyed this movie, without
    rating it.
    """
    await rating_service.dismiss_prompt(user.id, movie.id)


# -----------------------------------------------------------------------------
# MOVIES
# -----------------------------------------------------------------------------


@router.get("/movies/{movie_id}")
async def get_movie_rating(
    rating_service: rating_service_dep, user: current_user_dep, movie: movie_dep
) -> UserRating:
    """Get the current user's rating of a movie."""
    return UserRating(score=await rating_service.get_score(user.id, movie_id=movie.id))


@router.put("/movies/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def set_movie_rating(
    rating_service: rating_service_dep,
    user: current_user_dep,
    movie: movie_dep,
    rating: SetRating,
) -> None:
    """Rate a movie as the current user, replacing any previous rating."""
    await rating_service.set_score(user.id, rating.score, movie_id=movie.id)
    # The newly rated title may be a recommendation seed without a list yet.
    await enqueue_list_refresh()


@router.delete("/movies/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def clear_movie_rating(
    rating_service: rating_service_dep, user: current_user_dep, movie: movie_dep
) -> None:
    """Remove the current user's rating of a movie."""
    await rating_service.clear_score(user.id, movie_id=movie.id)


# -----------------------------------------------------------------------------
# SHOWS
# -----------------------------------------------------------------------------


@router.get("/shows/{show_id}")
async def get_show_rating(
    rating_service: rating_service_dep, user: current_user_dep, show: show_dep
) -> UserRating:
    """Get the current user's rating of a show."""
    return UserRating(score=await rating_service.get_score(user.id, show_id=show.id))


@router.put("/shows/{show_id}", status_code=status.HTTP_204_NO_CONTENT)
async def set_show_rating(
    rating_service: rating_service_dep,
    user: current_user_dep,
    show: show_dep,
    rating: SetRating,
) -> None:
    """Rate a show as the current user, replacing any previous rating."""
    await rating_service.set_score(user.id, rating.score, show_id=show.id)
    # The newly rated title may be a recommendation seed without a list yet.
    await enqueue_list_refresh()


@router.delete("/shows/{show_id}", status_code=status.HTTP_204_NO_CONTENT)
async def clear_show_rating(
    rating_service: rating_service_dep, user: current_user_dep, show: show_dep
) -> None:
    """Remove the current user's rating of a show."""
    await rating_service.clear_score(user.id, show_id=show.id)
