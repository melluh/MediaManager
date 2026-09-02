import Check from '@lucide/svelte/icons/check';
import CircleAlert from '@lucide/svelte/icons/circle-alert';
import CircleHelp from '@lucide/svelte/icons/circle-help';
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
 * in particular, "seeding" is always treated as "download complete" here,
 * since the file is fully downloaded either way.
 *
 * Download completion and import completion are separate steps (import runs
 * on a delayed background scan after the download finishes, and can fail on
 * its own). The "Finished" label is reserved for the fully-done case -
 * downloaded *and* imported - so a completed download still shows as
 * "Waiting for import" or "Import Failed" until the import step actually
 * succeeds, instead of looking done when it isn't.
 */
export function getDownloadStatusBadge(torrent: TorrentWithProgress): DownloadStatusBadge {
	const progress = torrent.download_progress;

	const downloadComplete = progress
		? progress.state === 'finished' || progress.state === 'seeding'
		: getTorrentStatusString(torrent.status) === 'finished';

	if (downloadComplete) {
		if (torrent.import_error) {
			return {
				variant: 'destructive',
				icon: CircleAlert,
				label: 'Import Failed',
				isFinished: true
			};
		}
		if (torrent.imported) {
			return { variant: 'default', icon: Check, label: 'Finished', isFinished: true };
		}
		return {
			variant: 'secondary',
			icon: Clock,
			label: 'Waiting for import',
			isFinished: true
		};
	}

	if (!progress) {
		// No live progress from the download client - fall back to the coarser,
		// persisted TorrentStatus. Handled explicitly (not piped through
		// getDownloadStateString) since TorrentStatus and DownloadState are
		// different vocabularies that only coincidentally share some values.
		const statusLabel = getTorrentStatusString(torrent.status);
		if (statusLabel === 'error') {
			return { variant: 'destructive', icon: CircleAlert, label: 'Error', isFinished: false };
		}
		if (statusLabel === 'downloading') {
			return { variant: 'outline', icon: Download, label: 'Downloading', isFinished: false };
		}
		return { variant: 'outline', icon: CircleHelp, label: 'Unknown', isFinished: false };
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
