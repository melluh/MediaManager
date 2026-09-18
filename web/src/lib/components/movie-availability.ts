import type { MovieTorrent, PublicMovie, PublicMovieFile } from '$lib/api/api';
import { getTorrentStatusString } from '$lib/utils';
import type { AvailabilityBadgeInfo, MediaAvailability } from './media-availability';

/** Short quality labels for the badge, e.g. "Available (1080p)". Quality 5
 * ("unknown") is deliberately absent - an unknown quality reads as no
 * quality info at all, not as a label worth showing. */
const qualityShortMap: Record<number, string> = {
	1: '4K',
	2: '1080p',
	3: '720p',
	4: '480p'
};

export function movieAvailability(
	movie: PublicMovie,
	movieFiles: PublicMovieFile[]
): MediaAvailability {
	const torrents = movie.torrents ?? [];
	const primary: AvailabilityBadgeInfo = movie.downloaded
		? { label: availableLabel(movieFiles), tone: 'available' }
		: notDownloadedLabel(torrents);

	const isDownloading = torrents.some((t) => getTorrentStatusString(t.status) === 'downloading');
	const secondary: AvailabilityBadgeInfo | undefined = isDownloading
		? { label: 'Downloading', tone: 'downloading' }
		: undefined;

	return { primary, secondary };
}

function availableLabel(movieFiles: PublicMovieFile[]): string {
	const bestQuality = movieFiles
		.filter((file) => file.downloaded)
		.reduce<
			number | null
		>((best, file) => (best === null || file.quality < best ? file.quality : best), null);
	const qualityLabel = bestQuality != null ? qualityShortMap[bestQuality] : undefined;
	return qualityLabel ? `Available (${qualityLabel})` : 'Available';
}

/**
 * When nothing is downloaded yet, distinguishes "a download errored out" and
 * "finished downloading but hasn't imported yet" from the plain "not
 * downloaded" case - torrents currently downloading are reported separately
 * as the secondary badge, so they're excluded here.
 */
function notDownloadedLabel(torrents: MovieTorrent[]): AvailabilityBadgeInfo {
	const settled = torrents.filter((t) => getTorrentStatusString(t.status) !== 'downloading');
	if (settled.some((t) => getTorrentStatusString(t.status) === 'finished' && !t.imported)) {
		return { label: 'Waiting for import', tone: 'neutral' };
	}
	if (settled.some((t) => getTorrentStatusString(t.status) === 'error')) {
		return { label: 'Download failed', tone: 'error' };
	}
	return { label: 'Not downloaded yet', tone: 'neutral' };
}
