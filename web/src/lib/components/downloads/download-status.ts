import Check from '@lucide/svelte/icons/check';
import CircleAlert from '@lucide/svelte/icons/circle-alert';
import Clock from '@lucide/svelte/icons/clock';
import Download from '@lucide/svelte/icons/download';
import type { TorrentWithProgress } from '$lib/api/api';
import type { BadgeVariant } from '$lib/components/ui/badge/index.js';
import { getDownloadStateString, getTorrentStatusString } from '$lib/utils';

export type DownloadStatusBadge = {
	variant: BadgeVariant;
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	icon: any;
	label: string;
	/** True once the download is complete, regardless of whether the client is still seeding it. */
	isFinished: boolean;
};

/**
 * Single source of truth for how a torrent's download status is presented
 * (badge variant, icon, label). Used by both the dashboard card and the
 * details dialog so they can never disagree on what state a torrent is in -
 * in particular, "seeding" is always treated as "finished" here, since the
 * file is fully downloaded either way.
 */
export function getDownloadStatusBadge(torrent: TorrentWithProgress): DownloadStatusBadge {
	const progress = torrent.download_progress;

	if (!progress) {
		// No live progress from the download client - fall back to the coarser,
		// persisted TorrentStatus. Handled explicitly (not piped through
		// getDownloadStateString) since TorrentStatus and DownloadState are
		// different vocabularies that only coincidentally share some values.
		const statusLabel = getTorrentStatusString(torrent.status);
		if (statusLabel === 'finished') {
			return { variant: 'default', icon: Check, label: 'Finished', isFinished: true };
		}
		if (statusLabel === 'error') {
			return { variant: 'destructive', icon: CircleAlert, label: 'Error', isFinished: false };
		}
		return {
			variant: 'outline',
			icon: Download,
			label: statusLabel === 'downloading' ? 'Downloading' : 'Unknown',
			isFinished: false
		};
	}

	if (progress.state === 'finished' || progress.state === 'seeding') {
		return { variant: 'default', icon: Check, label: 'Finished', isFinished: true };
	}
	if (progress.state === 'error') {
		return { variant: 'destructive', icon: CircleAlert, label: 'Error', isFinished: false };
	}
	if (progress.state === 'queued') {
		return { variant: 'secondary', icon: Clock, label: 'Queued', isFinished: false };
	}
	return {
		variant: 'outline',
		icon: Download,
		label: `${getDownloadStateString(progress.state)} ${Math.round(progress.progress)}%`,
		isFinished: false
	};
}
