import type { SeasonDownloadPlan } from '$lib/api/api';
import { padSeasonOrEpisodeNumber as pad } from '$lib/utils';

export type PlanSlot = SeasonDownloadPlan['slots'][number];
export type PlanPick = PlanSlot['picks'][number];
export type PlanGap = PlanSlot['gaps'][number];
export type PickStatus = 'starting' | 'started' | 'failed';

/** The first season/episode a pick covers, so picks list in viewing order. */
function pickSortKey(pick: PlanPick): [number, number] {
	if (pick.covers_episodes) {
		let best: [number, number] | null = null;
		for (const [seasonNumber, episodeNumbers] of Object.entries(pick.covers_episodes)) {
			for (const episodeNumber of episodeNumbers) {
				if (
					!best ||
					Number(seasonNumber) < best[0] ||
					(Number(seasonNumber) === best[0] && episodeNumber < best[1])
				) {
					best = [Number(seasonNumber), episodeNumber];
				}
			}
		}
		if (best) return best;
	}
	return [Math.min(...pick.covers_seasons), 0];
}

export function sortPicks(picks: PlanPick[]): PlanPick[] {
	return picks.slice().sort((a, b) => {
		const [aSeason, aEpisode] = pickSortKey(a);
		const [bSeason, bEpisode] = pickSortKey(b);
		return aSeason - bSeason || aEpisode - bEpisode;
	});
}

export function totalSize(picks: PlanPick[]): number {
	return picks.reduce((total, p) => total + p.result.size, 0);
}

/** E.g. "S01E01,E02", "S01" or "S01–S03". */
export function pickLabel(pick: PlanPick): string {
	if (pick.covers_episodes) {
		return Object.entries(pick.covers_episodes)
			.map(
				([seasonNumber, episodeNumbers]) =>
					`S${pad(Number(seasonNumber))}` + episodeNumbers.map((e) => `E${pad(e)}`).join(',')
			)
			.join(', ');
	}
	const seasons = pick.covers_seasons.slice().sort((a, b) => a - b);
	const first = `S${pad(seasons[0]!)}`;
	if (seasons.length === 1) return first;
	return `${first}–S${pad(seasons[seasons.length - 1]!)}`;
}

/** E.g. "S01 E03, E04". */
export function gapLabel(gap: PlanGap): string {
	return `S${pad(gap.season_number)} ${gap.episode_numbers.map((e) => `E${pad(e)}`).join(', ')}`;
}
