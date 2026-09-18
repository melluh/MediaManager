import type { PublicShow, RichSeasonTorrent } from '$lib/api/api';
import { formatSeasonRunLabel, getTorrentStatusString } from '$lib/utils';
import type { AvailabilityBadgeInfo, MediaAvailability } from './media-availability';

export type SeasonBannerState = 'available' | 'downloading' | 'partial' | 'missing' | 'unreleased';

export interface SeasonBanner {
	state: SeasonBannerState;
	label: string;
	classes: string;
}

export const seasonBannerClasses: Record<SeasonBannerState, string> = {
	available: 'bg-green-600/90',
	downloading: 'bg-blue-600/90',
	partial: 'bg-amber-600/90',
	missing: 'bg-gray-600/80',
	unreleased: 'bg-slate-600/80'
};

/**
 * Classifies a single season's download state - the single source of truth
 * shared by the per-season poster banner and the show-level availability
 * badge, so the two can never disagree about the same show.
 */
export function seasonBanner(
	season: PublicShow['seasons'][number],
	showTorrents: RichSeasonTorrent[]
): SeasonBanner {
	const total = season.episodes.length;
	const downloadedCount = season.episodes.filter((episode) => episode.downloaded).length;
	const allDownloaded = season.downloaded || (total > 0 && downloadedCount === total);

	if (allDownloaded) {
		return { state: 'available', label: 'Available', classes: seasonBannerClasses.available };
	}

	const isDownloading = showTorrents.some(
		(t) => t.seasons.includes(season.number) && getTorrentStatusString(t.status) === 'downloading'
	);
	if (isDownloading) {
		return {
			state: 'downloading',
			label: downloadedCount > 0 ? `Downloading (${downloadedCount}/${total})` : 'Downloading',
			classes: seasonBannerClasses.downloading
		};
	}
	if (downloadedCount > 0) {
		return {
			state: 'partial',
			label: `Partial (${downloadedCount}/${total})`,
			classes: seasonBannerClasses.partial
		};
	}
	// A future air_date is the clear signal, but a season with no episode
	// data yet (nothing announced) is just as clearly not downloadable.
	if (total === 0 || (season.air_date && new Date(season.air_date) > new Date())) {
		return { state: 'unreleased', label: 'Unreleased', classes: seasonBannerClasses.unreleased };
	}
	return { state: 'missing', label: 'Missing', classes: seasonBannerClasses.missing };
}

/**
 * Aggregates every season's banner into the show-level availability badge.
 * Only seasons that have actually aired factor into "fully available" - an
 * ongoing show's next (unreleased) season, or a specials season with no
 * episodes yet, must never keep the show from reading "Available".
 */
export function showAvailability(
	show: PublicShow,
	showTorrents: RichSeasonTorrent[]
): MediaAvailability {
	const released = show.seasons
		.map((season) => ({ season, banner: seasonBanner(season, showTorrents) }))
		.filter(({ banner }) => banner.state !== 'unreleased');

	const availableSeasons = released
		.filter(({ banner }) => banner.state === 'available')
		.map(({ season }) => season.number);
	const downloadingSeasons = released
		.filter(({ banner }) => banner.state === 'downloading')
		.map(({ season }) => season.number);

	let primary: AvailabilityBadgeInfo;
	if (released.length === 0) {
		primary = { label: 'Not downloaded yet', tone: 'neutral' };
	} else if (availableSeasons.length === released.length) {
		primary = { label: 'Available', tone: 'available' };
	} else if (availableSeasons.length > 0) {
		primary = { label: `${formatSeasonRunLabel(availableSeasons)} available`, tone: 'available' };
	} else {
		primary = { label: 'Not downloaded yet', tone: 'neutral' };
	}

	let secondary: AvailabilityBadgeInfo | undefined;
	if (downloadingSeasons.length > 0) {
		secondary = {
			label: `Downloading ${formatSeasonRunLabel(downloadingSeasons)}`,
			tone: 'downloading'
		};
	}

	return { primary, secondary };
}
