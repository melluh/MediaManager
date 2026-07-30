import type { SubtitleInfo } from '$lib/api/api';

export const hdrLabels: Record<string, string> = {
	hdr10: 'HDR10',
	hdr10plus: 'HDR10+',
	dv: 'Dolby Vision'
};

export function formatSize(bytes: number): string {
	return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`;
}

export function formatMbps(effectiveMbps: number | null | undefined): string {
	return effectiveMbps != null ? `${effectiveMbps.toFixed(1)} Mbps` : 'unknown';
}

export function formatSeeders(usenet: boolean, seeders: number): string {
	return usenet ? 'N/A' : String(seeders);
}

export function formatGroup(releaseGroup: string | null | undefined): string {
	return releaseGroup ?? 'unknown';
}

export function formatCodec(codec: string | null | undefined): string {
	return codec ?? 'unknown';
}

export function formatSubtitles(subtitles: SubtitleInfo[] | null | undefined): string {
	return subtitles && subtitles.length > 0
		? subtitles.map((s) => s.language).join(', ')
		: 'unknown';
}
