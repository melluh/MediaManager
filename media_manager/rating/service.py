import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from media_manager.auth.db import User
from media_manager.mediaServer.manager import get_media_server_provider
from media_manager.rating.repository import RatingRepository
from media_manager.rating.schemas import RatingPrompt

log = logging.getLogger(__name__)

RATING_PROMPT_LOOKBACK = timedelta(days=30)
"""How long after watching a movie the user is still asked whether they
enjoyed it."""

MAX_RATING_PROMPTS = 10


class RatingService:
    def __init__(self, rating_repository: RatingRepository) -> None:
        self.rating_repository = rating_repository

    async def get_score(
        self,
        user_id: UUID,
        *,
        movie_id: UUID | None = None,
        show_id: UUID | None = None,
    ) -> int | None:
        return await self.rating_repository.get_score(
            user_id, movie_id=movie_id, show_id=show_id
        )

    async def set_score(
        self,
        user_id: UUID,
        score: int,
        *,
        movie_id: UUID | None = None,
        show_id: UUID | None = None,
    ) -> None:
        await self.rating_repository.set_score(
            user_id, score, movie_id=movie_id, show_id=show_id
        )

    async def clear_score(
        self,
        user_id: UUID,
        *,
        movie_id: UUID | None = None,
        show_id: UUID | None = None,
    ) -> None:
        await self.rating_repository.delete_score(
            user_id, movie_id=movie_id, show_id=show_id
        )

    async def dismiss_prompt(self, user_id: UUID, movie_id: UUID) -> None:
        await self.rating_repository.dismiss_prompt(user_id, movie_id)

    async def get_rating_prompts(self, user: User) -> list[RatingPrompt]:
        """
        Library movies the user recently finished on the media server and
        hasn't rated or dismissed yet, most recently watched first. Empty when
        no media server is configured, the user has no account linked on it,
        or it can't be reached.
        """
        provider = get_media_server_provider()
        if provider is None:
            return []
        account = next(
            (a for a in user.media_server_accounts if a.provider == provider.name),
            None,
        )
        if account is None:
            return []

        try:
            played = await provider.get_recently_played_movies(
                account.external_user_id,
                since=datetime.now(UTC) - RATING_PROMPT_LOOKBACK,
            )
        except Exception:
            log.warning(
                f"Could not fetch recently played movies from {provider.display_name}",
                exc_info=True,
            )
            return []
        if not played:
            return []

        imdb_ids = {
            item.provider_ids["imdb"] for item in played if "imdb" in item.provider_ids
        }
        external_ids = {
            (provider_name, int(item.provider_ids[provider_name]))
            for item in played
            for provider_name in ("tmdb", "tvdb")
            if item.provider_ids.get(provider_name, "").isdigit()
        }
        movies = await self.rating_repository.find_movies(imdb_ids, external_ids)
        answered = await self.rating_repository.get_answered_movie_ids(user.id)

        prompts: list[RatingPrompt] = []
        seen: set[UUID] = set()
        # `played` is most recent first, so the first match for a movie is its
        # latest watch.
        for item in played:
            for movie, summary in movies:
                if movie.id in seen or movie.id in answered:
                    continue
                if _matches(
                    movie.imdb_id,
                    movie.metadata_provider,
                    movie.external_id,
                    item.provider_ids,
                ):
                    seen.add(movie.id)
                    prompts.append(
                        RatingPrompt(media=summary, watched_at=item.last_played_at)
                    )
                    break
            if len(prompts) >= MAX_RATING_PROMPTS:
                break
        return prompts


def _matches(
    imdb_id: str | None,
    metadata_provider: str,
    external_id: int,
    provider_ids: dict[str, str],
) -> bool:
    if imdb_id and provider_ids.get("imdb") == imdb_id:
        return True
    return provider_ids.get(metadata_provider) == str(external_id)
