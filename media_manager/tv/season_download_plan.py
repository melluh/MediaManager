"""
Turns a set of requested season numbers plus a pool of candidate torrents
into a `SeasonDownloadPlan`: one independent coverage plan per quality slot,
each the smallest, most consistent set of torrents that together cover every
episode of every requested season using only that slot's candidates.

Season-level releases (whole-series or single-season packs) are always
preferred over episode-level releases, which are only used to fill in
episodes of a season no pack could cover. Where a single release group can
supply full coverage on its own within a slot, that group's picks are
preferred over a mix of groups, for consistency across the resulting
downloads. Candidates are partitioned by slot before any of this runs, and
never compared across slots, since `result.score` is only ever a meaningful
ranking within its own slot - candidates that matched no configured slot are
dropped entirely, matching the app's existing convention for unslotted
results (see `torrent-grouping.ts::groupIntoSlots` on the frontend).
"""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from media_manager.indexer.schemas import IndexerQueryResult
from media_manager.tv.schemas import (
    CoverageGap,
    EpisodeNumber,
    Season,
    SeasonDownloadPlan,
    SeasonNumber,
    SlotDownloadPlan,
    SuggestedTorrentPick,
)

Pair = tuple[SeasonNumber, EpisodeNumber]


@dataclass
class _InternalPick:
    result: IndexerQueryResult
    pairs: set[Pair]


def _quality_key(result: IndexerQueryResult) -> tuple[int, int]:
    """Lower is better - matches the (slot_index, -score) ordering that
    already defines "best" for a single-season search elsewhere in the app."""
    slot = result.slot_index if result.slot_index is not None else 10_000
    return (slot, -result.score)


def _release_group(result: IndexerQueryResult) -> str | None:
    return result.attributes.release_group if result.attributes else None


def _group_bias(result: IndexerQueryResult, picks_so_far: list[_InternalPick]) -> int:
    """0 if this candidate's release group already appears among accepted
    picks (a soft nudge toward fewer distinct groups), else 1."""
    group = _release_group(result)
    if group is None:
        return 1
    return 0 if any(_release_group(p.result) == group for p in picks_so_far) else 1


def _solve(
    candidates: list[IndexerQueryResult],
    required_pairs: set[Pair],
    season_number_set: set[SeasonNumber],
    episodes_by_season: dict[SeasonNumber, list[EpisodeNumber]],
) -> tuple[list[_InternalPick], set[Pair]]:
    season_level = [c for c in candidates if not c.episode]
    episode_level = [c for c in candidates if c.episode]

    picks: list[_InternalPick] = []
    covered: set[Pair] = set()
    # Every native season touched by an accepted season-level pick - once a
    # season is in here, no later pick (of either kind) may touch it again,
    # which is what stops two accepted downloads from both trying to write
    # episode-file rows for the same season.
    claimed_seasons: set[SeasonNumber] = set()

    remaining_season_level = list(season_level)
    while True:
        scored = []
        for c in remaining_season_level:
            native = set(c.season)
            if native & claimed_seasons:
                continue
            new_seasons = native & season_number_set
            if not new_seasons:
                continue
            key = (-len(new_seasons), _group_bias(c, picks), _quality_key(c))
            scored.append((key, c, new_seasons))
        if not scored:
            break
        _, best, best_new_seasons = min(scored, key=lambda t: t[0])
        remaining_season_level.remove(best)
        claimed_seasons |= set(best.season)
        pairs = {
            (s, e) for s in best_new_seasons for e in episodes_by_season.get(s, [])
        }
        covered |= pairs
        picks.append(_InternalPick(result=best, pairs=pairs))

    leftover_seasons = season_number_set - claimed_seasons
    remaining_episode_level = [
        c for c in episode_level if set(c.season) & leftover_seasons
    ]
    remaining_pairs = required_pairs - covered
    while remaining_pairs:
        scored = []
        for c in remaining_episode_level:
            candidate_pairs = {
                (s, e) for s in c.season if s in leftover_seasons for e in c.episode
            }
            new_pairs = candidate_pairs & remaining_pairs
            if not new_pairs:
                continue
            key = (-len(new_pairs), _group_bias(c, picks), _quality_key(c))
            scored.append((key, c, new_pairs))
        if not scored:
            break
        _, best, best_new_pairs = min(scored, key=lambda t: t[0])
        remaining_episode_level.remove(best)
        covered |= best_new_pairs
        remaining_pairs -= best_new_pairs
        picks.append(_InternalPick(result=best, pairs=best_new_pairs))

    return picks, covered


def _to_suggested_pick(
    pick: _InternalPick, downloaded_by_pair: Mapping[Pair, bool]
) -> SuggestedTorrentPick:
    covers_seasons = sorted({s for s, _ in pick.pairs})
    is_episode_level = bool(pick.result.episode)
    covers_episodes: dict[SeasonNumber, list[EpisodeNumber]] | None = None
    if is_episode_level:
        by_season: dict[SeasonNumber, list[EpisodeNumber]] = defaultdict(list)
        for season_number, episode_number in sorted(pick.pairs):
            by_season[season_number].append(episode_number)
        covers_episodes = dict(by_season)
    return SuggestedTorrentPick(
        result=pick.result,
        covers_seasons=covers_seasons,
        covers_episodes=covers_episodes,
        already_downloaded=all(
            downloaded_by_pair.get(pair, False) for pair in pick.pairs
        ),
    )


def _build_gaps(missing_pairs: set[Pair]) -> list[CoverageGap]:
    if not missing_pairs:
        return []
    by_season: dict[SeasonNumber, list[EpisodeNumber]] = defaultdict(list)
    for season_number, episode_number in sorted(missing_pairs):
        by_season[season_number].append(episode_number)
    return [
        CoverageGap(
            season_number=season_number,
            episode_numbers=episode_numbers,
            reason="No suitable torrent found.",
        )
        for season_number, episode_numbers in sorted(by_season.items())
    ]


def _solve_slot_candidates(
    candidates: list[IndexerQueryResult],
    required_pairs: set[Pair],
    season_number_set: set[SeasonNumber],
    episodes_by_season: dict[SeasonNumber, list[EpisodeNumber]],
) -> tuple[list[_InternalPick], set[Pair]]:
    """
    Prefer a single release group that alone covers everything (for
    consistency across the resulting downloads), falling back to mixing
    groups when no single one suffices. Only ever called with candidates
    already narrowed to one quality slot, so `result.score` comparisons
    here are always within-slot and therefore meaningful.
    """
    groups: dict[str, list[IndexerQueryResult]] = defaultdict(list)
    for candidate in candidates:
        group = _release_group(candidate)
        if group is not None:
            groups[group].append(candidate)

    best_group_solution: tuple[int, list[_InternalPick], set[Pair]] | None = None
    for group_candidates in groups.values():
        picks, covered = _solve(
            group_candidates, required_pairs, season_number_set, episodes_by_season
        )
        if covered == required_pairs and required_pairs:
            total_score = sum(pick.result.score for pick in picks)
            if best_group_solution is None or total_score > best_group_solution[0]:
                best_group_solution = (total_score, picks, covered)

    if best_group_solution is not None:
        return best_group_solution[1], best_group_solution[2]
    return _solve(candidates, required_pairs, season_number_set, episodes_by_season)


def build_season_download_plan(
    season_numbers: Sequence[SeasonNumber],
    seasons: Sequence[Season],
    candidates: Sequence[IndexerQueryResult],
    downloaded_by_pair: Mapping[Pair, bool],
    search_errors: Sequence[str] = (),
) -> SeasonDownloadPlan:
    season_number_set = {SeasonNumber(n) for n in season_numbers}
    episodes_by_season: dict[SeasonNumber, list[EpisodeNumber]] = {
        season.number: [episode.number for episode in season.episodes]
        for season in seasons
        if season.number in season_number_set
    }
    required_pairs: set[Pair] = {
        (season_number, episode_number)
        for season_number, episode_numbers in episodes_by_season.items()
        for episode_number in episode_numbers
    }

    by_slot: dict[str, list[IndexerQueryResult]] = defaultdict(list)
    for candidate in candidates:
        if candidate.slot_name is not None:
            by_slot[candidate.slot_name].append(candidate)

    slot_plans: list[SlotDownloadPlan] = []
    for slot_candidates in by_slot.values():
        picks, covered = _solve_slot_candidates(
            slot_candidates, required_pairs, season_number_set, episodes_by_season
        )
        if not picks:
            continue
        first = slot_candidates[0]
        slot_plans.append(
            SlotDownloadPlan(
                slot_name=first.slot_name,
                slot_label=first.slot_label or first.slot_name,
                slot_index=first.slot_index if first.slot_index is not None else 10_000,
                picks=[_to_suggested_pick(pick, downloaded_by_pair) for pick in picks],
                gaps=_build_gaps(required_pairs - covered),
            )
        )

    slot_plans.sort(key=lambda plan: plan.slot_index)

    return SeasonDownloadPlan(slots=slot_plans, search_errors=list(search_errors))
