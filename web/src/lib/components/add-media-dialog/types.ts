import { Signal, SignalHigh, SignalLow, SignalMedium } from 'lucide-svelte';
import type { IndexerQueryResult } from '$lib/api/api';

// Ordered list of pages shown in the add-media dialog. Adding a page (e.g. a
// future "seasons" step for shows) means adding an id here and a matching
// case in add-media-dialog.svelte's page/footer switch.
export type AddMediaPageId = 'details' | 'download';

export type MediaQuality = '4k' | '1080p' | '720p' | 'lower';

export const qualityOptions: {
	value: MediaQuality;
	label: string;
	sublabel: string;
	// This should be `Component` after @lucide/svelte updates types
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	icon: any;
}[] = [
	{ value: '4k', label: 'UHD', sublabel: '4K', icon: Signal },
	{ value: '1080p', label: 'Full HD', sublabel: '1080p', icon: SignalHigh },
	{ value: '720p', label: 'HD', sublabel: '720p', icon: SignalMedium },
	{ value: 'lower', label: 'SD', sublabel: '480p or lower', icon: SignalLow }
];

export type QualityCounts = Record<MediaQuality, number>;

// Maps the backend's numeric torrent quality (1 = 4K/UHD .. 5 = unknown) onto
// our four-tier quality buckets, folding the bottom two (SD/unknown) into "lower".
export function bucketTorrentQuality(quality: number): MediaQuality {
	if (quality === 1) return '4k';
	if (quality === 2) return '1080p';
	if (quality === 3) return '720p';
	return 'lower';
}

// The highest quality tier that has at least one torrent, in "1080p/Full HD" style.
export function getBestAvailableQuality(counts: QualityCounts): MediaQuality | undefined {
	return qualityOptions.map((quality) => quality.value).find((value) => counts[value] > 0);
}

export function getQualitySummaryLabel(quality: MediaQuality): string {
	const option = qualityOptions.find((q) => q.value === quality);
	if (!option) return '';
	return quality === 'lower' ? option.label : `${option.sublabel}/${option.label}`;
}

export type SelectedTorrents = Partial<Record<MediaQuality, IndexerQueryResult>>;

// Torrents already arrive best-first within each quality tier (the backend's
// evaluate_indexer_query_results sorts by quality, then score, then
// usenet/age/seeders/size), so the first one seen per bucket is the one that
// would actually be picked for a download at that quality.
export function getBestTorrentPerQuality(torrents: IndexerQueryResult[]): SelectedTorrents {
	const map: SelectedTorrents = {};
	for (const torrent of torrents) {
		const bucket = bucketTorrentQuality(torrent.quality);
		if (!(bucket in map)) map[bucket] = torrent;
	}
	return map;
}

export function formatTorrentSize(bytes: number): string {
	return `${(bytes / 1024 / 1024 / 1024).toFixed(2)}GB`;
}

// `new Date("YYYY-MM-DD")` parses the string as UTC midnight, which lands on
// the previous or next local calendar day depending on the viewer's timezone
// offset. Parsing the components directly and building a local Date keeps
// "today" comparisons accurate everywhere.
function parseDateOnlyLocal(dateString: string): Date | null {
	const match = dateString.match(/^(\d{4})-(\d{2})-(\d{2})/);
	if (!match) {
		const fallback = new Date(dateString);
		return Number.isNaN(fallback.getTime()) ? null : fallback;
	}
	const [, year, month, day] = match;
	return new Date(Number(year), Number(month) - 1, Number(day));
}

function startOfToday(): Date {
	const today = new Date();
	today.setHours(0, 0, 0, 0);
	return today;
}

export function isReleaseUpcoming(releaseDate: string | null | undefined): boolean {
	if (!releaseDate) return false;
	const parsed = parseDateOnlyLocal(releaseDate);
	if (!parsed) return false;
	return parsed.getTime() > startOfToday().getTime();
}

function withOrdinalSuffix(monthAndDay: string): string {
	const match = monthAndDay.match(/\d+$/);
	if (!match) return monthAndDay;
	const day = Number(match[0]);
	const suffix =
		day % 10 === 1 && day !== 11
			? 'st'
			: day % 10 === 2 && day !== 12
				? 'nd'
				: day % 10 === 3 && day !== 13
					? 'rd'
					: 'th';
	return monthAndDay.replace(/\d+$/, `${day}${suffix}`);
}

// "Releases in 3 days (July 30th)" for near-term dates, "Releases Sep 1, 2028"
// once it's far enough out that a relative count stops being useful.
export function getUpcomingReleaseLabel(releaseDate: string): string {
	const release = parseDateOnlyLocal(releaseDate) ?? new Date(releaseDate);
	const today = startOfToday();

	const daysUntil = Math.round((release.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

	if (daysUntil <= 30) {
		const relative = daysUntil === 1 ? 'tomorrow' : `in ${daysUntil} days`;
		const formatted = withOrdinalSuffix(
			release.toLocaleDateString('en-US', { month: 'long', day: 'numeric' })
		);
		return `Releases ${relative} (${formatted})`;
	}

	const formatted = release.toLocaleDateString('en-US', {
		month: 'short',
		day: 'numeric',
		year: 'numeric'
	});
	return `Releases ${formatted}`;
}
