"""
Personal recommendations, item-based: every title the user rated or watched
(a "seed") votes for the titles TMDB lists as liked by the same people,
weighted by the user's opinion of the seed and the title's rank in that list.
Seeds the user disliked vote against their list, and a small genre-taste and
quality bonus breaks ties.
"""

import asyncio
import logging
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from media_manager.metadataProvider.abstract_metadata_provider import (
    AbstractMetadataProvider,
)
from media_manager.metadataProvider.schemas import (
    MediaType,
    MetaDataProviderSearchResult,
)
from media_manager.recommendation.models import TmdbRecommendationList
from media_manager.recommendation.repository import RecommendationRepository
from media_manager.recommendation.schemas import PersonalRecommendation, RatedMedia
from media_manager.watch_history.service import WatchHistoryService

log = logging.getLogger(__name__)

LIST_MAX_AGE = timedelta(days=7)
"""How long a stored TMDB list is used before it's fetched again. These lists
change slowly."""
FAILED_LIST_RETRY_AFTER = timedelta(days=1)
"""How long to wait before retrying a list whose fetch failed, e.g. because
the metadata relay doesn't offer recommendations yet."""

MAX_SEEDS = 30
"""Seeds used per user and media type, strongest opinions first - bounds the
TMDB lists that need to be fetched and kept fresh per user."""
MAX_RECOMMENDATIONS = 20
MAX_PER_REASON = 4
"""Most recommendations credited to the same seed, so one loved title can't
fill the whole list."""

WATCHED_WEIGHT = 0.5
"""Weight of a title the user watched but didn't rate: choosing to watch
something is a weak sign of liking it. A rating's weight is its score."""
RECENCY_HALF_LIFE = timedelta(days=365)
MIN_RECENCY_FACTOR = 0.25
"""Old opinions count for less, but never for nothing."""
RANK_DECAY = 5
"""A title's vote from a seed's list halves by this rank, and keeps falling."""
GENRE_WEIGHT = 0.5
QUALITY_WEIGHT = 0.2
NEUTRAL_VOTE_AVERAGE = 6.5
"""TMDB vote average that earns no quality bonus or penalty."""

_MAX_CONCURRENT_LIST_FETCHES = 4


class WatchedTitle(Protocol):
    name: str
    imdb_id: str | None
    tmdb_id: int | None
    tvdb_id: int | None
    last_played_at: datetime | None


@dataclass(frozen=True)
class Seed:
    """A title the user has an opinion on, as a TMDB id to look up lists for."""

    tmdb_id: int
    name: str
    weight: float
    """Signed: negative seeds vote against the titles in their list."""
    score: int | None
    """The user's rating, or None if they only watched it."""


def recency_factor(at: datetime | None, now: datetime) -> float:
    if at is None:
        return MIN_RECENCY_FACTOR
    half_lives = max((now - at) / RECENCY_HALF_LIFE, 0)
    return max(0.5**half_lives, MIN_RECENCY_FACTOR)


def build_seeds(
    rated: Sequence[RatedMedia], watched: Sequence[WatchedTitle], now: datetime
) -> tuple[list[Seed], set[int]]:
    """
    :return: The strongest `MAX_SEEDS` seeds, and the TMDB id of every title
        the user rated or watched - which are never worth recommending.
    """
    # Library titles from another metadata provider have no TMDB id of their
    # own, but the media server often knows it.
    tmdb_by_imdb = {w.imdb_id: w.tmdb_id for w in watched if w.imdb_id and w.tmdb_id}
    tmdb_by_tvdb = {w.tvdb_id: w.tmdb_id for w in watched if w.tvdb_id and w.tmdb_id}

    seeds: dict[int, Seed] = {}
    known: set[int] = set()
    for media in rated:
        if media.metadata_provider == "tmdb":
            tmdb_id = media.external_id
        else:
            tmdb_id = tmdb_by_imdb.get(media.imdb_id or "") or (
                tmdb_by_tvdb.get(media.external_id)
                if media.metadata_provider == "tvdb"
                else None
            )
        if tmdb_id is None:
            continue
        known.add(tmdb_id)
        if media.score:
            seeds[tmdb_id] = Seed(
                tmdb_id=tmdb_id,
                name=media.name,
                weight=media.score * recency_factor(media.rated_at, now),
                score=media.score,
            )
    rated_ids = set(known)
    for watch in watched:
        if watch.tmdb_id is None:
            continue
        known.add(watch.tmdb_id)
        if watch.tmdb_id not in rated_ids:
            seeds[watch.tmdb_id] = Seed(
                tmdb_id=watch.tmdb_id,
                name=watch.name,
                weight=WATCHED_WEIGHT * recency_factor(watch.last_played_at, now),
                score=None,
            )

    strongest = sorted(seeds.values(), key=lambda s: abs(s.weight), reverse=True)
    return strongest[:MAX_SEEDS], known


def genre_profile(rated: Sequence[RatedMedia]) -> dict[str, float]:
    """
    How much the user likes each genre, from -1 to 1, shrunk towards 0 for
    genres they rated few titles of.
    """
    totals: dict[str, float] = defaultdict(float)
    magnitudes: dict[str, float] = defaultdict(float)
    counts: Counter[str] = Counter()
    for media in rated:
        for genre in media.genres:
            totals[genre] += media.score
            magnitudes[genre] += abs(media.score)
            counts[genre] += 1
    return {
        genre: totals[genre] / magnitudes[genre] * counts[genre] / (counts[genre] + 2)
        for genre in totals
        if magnitudes[genre]
    }


def _bonus(result: MetaDataProviderSearchResult, profile: dict[str, float]) -> float:
    bonus = 0.0
    if result.genres:
        bonus += (
            GENRE_WEIGHT
            * sum(profile.get(genre, 0.0) for genre in result.genres)
            / len(result.genres)
        )
    if result.vote_average:
        bonus += (
            QUALITY_WEIGHT
            * (result.vote_average - NEUTRAL_VOTE_AVERAGE)
            / (10 - NEUTRAL_VOTE_AVERAGE)
        )
    return bonus


def rank_candidates(
    seeds: Sequence[Seed],
    lists: dict[int, list[MetaDataProviderSearchResult]],
    profile: dict[str, float],
    exclude: set[int],
) -> list[PersonalRecommendation]:
    """
    Scores every title in the seeds' lists and returns the best, each
    credited to the seed that voted for it most.

    :param lists: TMDB recommendation list per seed TMDB id. Seeds without one
        don't vote.
    :param exclude: TMDB ids never to recommend.
    """
    totals: dict[int, float] = defaultdict(float)
    best: dict[int, tuple[float, Seed]] = {}
    candidates: dict[int, MetaDataProviderSearchResult] = {}
    for seed in seeds:
        for rank, result in enumerate(lists.get(seed.tmdb_id, [])):
            tmdb_id = result.external_id
            if tmdb_id in exclude or not result.poster_images:
                continue
            vote = seed.weight / (1 + rank / RANK_DECAY)
            totals[tmdb_id] += vote
            candidates.setdefault(tmdb_id, result)
            if vote > 0 and vote > best.get(tmdb_id, (0.0, seed))[0]:
                best[tmdb_id] = (vote, seed)

    scored = []
    for tmdb_id, total in totals.items():
        # Only recommend what something the user liked actually led to.
        if tmdb_id not in best:
            continue
        score = total + _bonus(candidates[tmdb_id], profile)
        if score > 0:
            scored.append((score, tmdb_id))
    scored.sort(reverse=True)

    recommendations: list[PersonalRecommendation] = []
    per_reason: Counter[int] = Counter()
    for _, tmdb_id in scored:
        reason = best[tmdb_id][1]
        if per_reason[reason.tmdb_id] >= MAX_PER_REASON:
            continue
        per_reason[reason.tmdb_id] += 1
        recommendations.append(
            PersonalRecommendation(
                media=candidates[tmdb_id],
                because_of=reason.name,
                because_score=reason.score,
            )
        )
        if len(recommendations) >= MAX_RECOMMENDATIONS:
            break
    return recommendations


def needs_refresh(stored: TmdbRecommendationList | None, now: datetime) -> bool:
    if stored is None:
        return True
    max_age = LIST_MAX_AGE if stored.results is not None else FAILED_LIST_RETRY_AFTER
    return now - stored.fetched_at >= max_age


async def enqueue_list_refresh() -> None:
    """
    Fetches missing or stale lists in the background. Never raises: callers
    have already done their actual work.
    """
    # Imported lazily: media_manager.scheduler imports the services that
    # import this module.
    from media_manager.scheduler import refresh_recommendation_lists_task

    try:
        await refresh_recommendation_lists_task.kiq()
    except Exception:
        log.warning("Could not enqueue recommendation list refresh", exc_info=True)


class RecommendationService:
    def __init__(
        self,
        recommendation_repository: RecommendationRepository,
        watch_history_service: WatchHistoryService,
        tmdb_provider: AbstractMetadataProvider,
    ) -> None:
        self.recommendation_repository = recommendation_repository
        self.watch_history_service = watch_history_service
        self.tmdb_provider = tmdb_provider

    async def __get_seeds(
        self, user_id: UUID, media_type: MediaType, now: datetime
    ) -> tuple[list[Seed], set[int], list[RatedMedia]]:
        rated = await self.recommendation_repository.get_rated_media(
            user_id, media_type
        )
        watched = await self.watch_history_service.get_watches(user_id, media_type)
        seeds, known = build_seeds(rated, watched, now)
        return seeds, known, rated

    async def get_recommendations(
        self, user_id: UUID, media_type: MediaType
    ) -> list[PersonalRecommendation]:
        """
        Movies or shows the user will probably like, best first, leaving out
        anything they rated or watched. Empty until they've rated or watched
        something, and until the TMDB lists for those titles are fetched -
        which this starts in the background if needed.
        """
        now = datetime.now(UTC)
        seeds, known, rated = await self.__get_seeds(user_id, media_type, now)
        if not seeds:
            return []

        stored = await self.recommendation_repository.get_lists(
            media_type, {seed.tmdb_id for seed in seeds}
        )
        if any(needs_refresh(stored.get(seed.tmdb_id), now) for seed in seeds):
            await enqueue_list_refresh()

        lists = {
            tmdb_id: [
                MetaDataProviderSearchResult.model_validate(result)
                for result in row.results
            ]
            for tmdb_id, row in stored.items()
            if row.results
        }
        recommendations = rank_candidates(seeds, lists, genre_profile(rated), known)

        library = await self.recommendation_repository.find_library_media(
            media_type, {r.media.external_id for r in recommendations}
        )
        for recommendation in recommendations:
            if match := library.get(recommendation.media.external_id):
                recommendation.media.added = True
                recommendation.media.id, recommendation.media.slug = match
        return recommendations

    async def refresh_stale_lists(self) -> None:
        """Fetches every user's missing or stale seed lists from TMDB."""
        now = datetime.now(UTC)
        stale: set[tuple[MediaType, int]] = set()
        for user_id in await self.recommendation_repository.get_user_ids_with_history():
            for media_type in MediaType:
                seeds, _, _ = await self.__get_seeds(user_id, media_type, now)
                stored = await self.recommendation_repository.get_lists(
                    media_type, {seed.tmdb_id for seed in seeds}
                )
                stale.update(
                    (media_type, seed.tmdb_id)
                    for seed in seeds
                    if needs_refresh(stored.get(seed.tmdb_id), now)
                )
        if not stale:
            return

        semaphore = asyncio.Semaphore(_MAX_CONCURRENT_LIST_FETCHES)

        async def fetch(
            media_type: MediaType, tmdb_id: int
        ) -> list[MetaDataProviderSearchResult] | None:
            async with semaphore:
                try:
                    return await self.tmdb_provider.get_recommendations(
                        tmdb_id, media_type
                    )
                except Exception:
                    log.debug(
                        f"Could not fetch TMDB recommendations for {media_type.value} {tmdb_id}",
                        exc_info=True,
                    )
                    return None

        keys = sorted(stale)
        results = await asyncio.gather(*(fetch(*key) for key in keys))
        # Saved one by one afterwards: the session can't be shared by the
        # concurrent fetches.
        for (media_type, tmdb_id), result in zip(keys, results, strict=True):
            await self.recommendation_repository.save_list(media_type, tmdb_id, result)

        failed = sum(result is None for result in results)
        log.info(f"Refreshed {len(keys) - failed} TMDB recommendation lists")
        if failed:
            log.warning(
                f"Could not fetch {failed} TMDB recommendation lists; retrying in "
                f"{FAILED_LIST_RETRY_AFTER}. Does the metadata relay offer them?"
            )
