import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { goto } from '$app/navigation';
import { resolve } from '$app/paths';
import { toast } from 'svelte-sonner';
import client from '$lib/api';
import type { Show, Movie } from '$lib/api/api';

export const qualityMap: { [key: number]: string } = {
	1: '4K/UHD',
	2: '1080p/FullHD',
	3: '720p/HD',
	4: '480p/SD',
	5: 'unknown'
};
export const torrentStatusMap: { [key: number]: string } = {
	1: 'finished',
	2: 'downloading',
	3: 'error',
	4: 'unknown'
};
export const downloadStateMap: { [key: string]: string } = {
	downloading: 'Downloading',
	queued: 'Queued',
	stalled: 'Stalled',
	checking: 'Checking',
	stopped: 'Stopped',
	seeding: 'Seeding',
	finished: 'Finished',
	error: 'Error',
	unknown: 'Unknown'
};

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

export function withoutTrailingSlash(pathname: string): string {
	return pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname;
}

export function isSearchPage(pathname: string): boolean {
	return withoutTrailingSlash(pathname) === withoutTrailingSlash(resolve('/dashboard/search', {}));
}

export function getTorrentQualityString(value: number): string {
	return qualityMap[value] || 'unknown';
}

export function getTorrentStatusString(value: number): string {
	return torrentStatusMap[value] || 'unknown';
}

export function getDownloadStateString(value: string): string {
	return downloadStateMap[value] || 'Unknown';
}

export function formatBytes(bytes: number | null | undefined): string | null {
	if (bytes == null || bytes < 0) return null;
	if (bytes === 0) return '0 B';
	const units = ['B', 'KB', 'MB', 'GB', 'TB'];
	const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
	const value = bytes / 1024 ** exponent;
	return `${exponent === 0 ? value : value.toFixed(1)} ${units[exponent]}`;
}

export function getFullyQualifiedMediaName(media: { name: string; year: number | null }): string {
	let name = media.name;
	if (media.year != null) {
		name += ' (' + media.year + ')';
	}
	return name;
}

export function convertTorrentSeasonRangeToIntegerRange(seasons: number[]): string {
	if (seasons.length === 1) return seasons[0]?.toString() || 'unknown';
	else if (seasons.length > 1) {
		const lastSeason = seasons.at(-1);
		return seasons[0]?.toString() + '-' + (lastSeason?.toString() || 'unknown');
	} else {
		console.log('Error parsing season range: ' + seasons);
		return 'Error parsing season range: ' + seasons;
	}
}

export function convertTorrentEpisodeRangeToIntegerRange(episodes: number[]): string {
	if (episodes.length === 1) return episodes[0]?.toString() || 'unknown';
	else if (episodes.length > 1) {
		const lastEpisode = episodes.at(-1);
		return episodes[0]?.toString() + '-' + (lastEpisode?.toString() || 'unknown');
	} else {
		console.log('Error parsing episode range: ' + episodes);
		return 'Error parsing episode range: ' + episodes;
	}
}

export async function handleLogout() {
	await client.POST('/api/v1/auth/cookie/logout');
	await goto(resolve('/login', {}));
}

export async function handleOauth() {
	const { error, data } = await client.GET(`/api/v1/auth/oauth/authorize`, {
		params: {
			query: {
				scopes: ['openid', 'email', 'profile']
			}
		}
	});
	if (!error && data?.authorization_url) {
		window.location.href = data.authorization_url;
	} else {
		toast.error('Failed to initiate OAuth login.');
	}
}

export function formatSecondsToOptimalUnit(seconds: number): string {
	if (seconds < 0) return '0s';

	const units = [
		{ name: 'y', seconds: 365.25 * 24 * 60 * 60 }, // year (accounting for leap years)
		{ name: 'mo', seconds: 30.44 * 24 * 60 * 60 }, // month (average)
		{ name: 'd', seconds: 24 * 60 * 60 }, // day
		{ name: 'h', seconds: 60 * 60 }, // hour
		{ name: 'm', seconds: 60 }, // minute
		{ name: 's', seconds: 1 } // second
	];

	for (const unit of units) {
		const value = seconds / unit.seconds;
		if (value >= 1) {
			return `${Math.floor(value)}${unit.name}`;
		}
	}

	return '0s';
}

export function formatRuntime(minutes: number | null | undefined): string | null {
	if (!minutes || minutes <= 0) return null;
	const hours = Math.floor(minutes / 60);
	const remainingMinutes = minutes % 60;
	if (hours === 0) return `${remainingMinutes}m`;
	if (remainingMinutes === 0) return `${hours}h`;
	return `${hours}h ${remainingMinutes}m`;
}

export function getLanguageDisplayName(languageCode: string | null | undefined): string | null {
	if (!languageCode) return null;
	try {
		return new Intl.DisplayNames(['en'], { type: 'language' }).of(languageCode) ?? languageCode;
	} catch {
		return languageCode;
	}
}

export function formatReleaseDate(date: string | null | undefined): string | null {
	if (!date) return null;
	const parsed = new Date(date);
	if (Number.isNaN(parsed.getTime())) return date;
	return parsed.toLocaleDateString(undefined, {
		year: 'numeric',
		month: 'long',
		day: 'numeric'
	});
}

const metadataProviderLabels: { [key: string]: string } = {
	tmdb: 'TMDB',
	tvdb: 'TVDB'
};

export function getMetadataProviderLabel(metadataProvider: string): string {
	return metadataProviderLabels[metadataProvider] ?? metadataProvider.toUpperCase();
}

export function getMetadataProviderUrl(
	metadataProvider: string,
	externalId: number,
	isShow: boolean
): string | null {
	switch (metadataProvider) {
		case 'tmdb':
			return `https://www.themoviedb.org/${isShow ? 'tv' : 'movie'}/${externalId}`;
		case 'tvdb':
			return `https://www.thetvdb.com/dereferrer/${isShow ? 'series' : 'movie'}/${externalId}`;
		default:
			return null;
	}
}

export function formatLastUpdated(date: string | null | undefined): string | null {
	if (!date) return null;
	const parsed = new Date(date);
	if (Number.isNaN(parsed.getTime())) return null;
	return parsed.toLocaleString(undefined, {
		year: 'numeric',
		month: 'short',
		day: 'numeric',
		hour: 'numeric',
		minute: '2-digit'
	});
}

export function handleQueryNotificationToast(count: number = 0, query: string = '') {
	if (count > 0 && query.length > 0)
		toast.success(`Found ${count} ${count > 1 ? 'result' : 'results'} for search term "${query}".`);
	else if (count == 0) toast.info(`No results found for "${query}".`);
}

export function saveDirectoryPreview(media: Show | Movie, filePathSuffix: string = '') {
	let path =
		'/' +
		getFullyQualifiedMediaName(media) +
		' [' +
		media.metadata_provider +
		'id-' +
		media.external_id +
		']/';
	if ('seasons' in media) {
		path += ' Season XX/SXXEXX' + (filePathSuffix === '' ? '' : ' - ' + filePathSuffix) + '.mkv';
	} else {
		path += media.name + (filePathSuffix === '' ? '' : ' - ' + filePathSuffix) + '.mkv';
	}
	return path;
}
