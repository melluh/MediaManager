<script lang="ts" module>
	import type { PublicEpisodeFile, PublicMovieFile } from '$lib/api/api';

	/**
	 * Movie and episode files share the `PublicMediaFile` base, so anything that
	 * only touches the shared fields can accept either.
	 */
	export type MediaFile = PublicMovieFile | PublicEpisodeFile;

	/** Whether two records are the same file: a movie/episode has one file per suffix. */
	export function isSameMediaFile(a: MediaFile, b: MediaFile): boolean {
		const ownerId = (file: MediaFile) => ('movie_id' in file ? file.movie_id : file.episode_id);
		return ownerId(a) === ownerId(b) && a.file_path_suffix === b.file_path_suffix;
	}
</script>

<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import TorrentStat from '$lib/components/download-dialogs/torrent-stat.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import SubtitleTrackList from '$lib/components/subtitle-track-list.svelte';
	import DeleteMediaFileDialog from '$lib/components/delete-media-file-dialog.svelte';
	import { formatAudioChannels } from '$lib/components/media-file-format';
	import AudioLines from '@lucide/svelte/icons/audio-lines';
	import Clock from '@lucide/svelte/icons/clock';
	import FileQuestionMark from '@lucide/svelte/icons/file-question-mark';
	import Film from '@lucide/svelte/icons/film';
	import HardDrive from '@lucide/svelte/icons/hard-drive';
	import MonitorPlay from '@lucide/svelte/icons/monitor-play';
	import Package from '@lucide/svelte/icons/package';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import { getCurrentUser } from '$lib/context.svelte';
	import { formatBytes, formatSecondsToOptimalUnit, getQualityString } from '$lib/utils';

	let {
		file,
		onDeleted
	}: {
		file: MediaFile;
		/** Called after the file was deleted, so the owner can close this dialog and refresh. */
		onDeleted?: () => void;
	} = $props();

	let user = getCurrentUser();
	let deleteConfirmOpen = $state(false);

	const UNKNOWN = 'unknown';

	// `details` is only populated when the file was actually found and probed;
	// every field inside it is independently optional, because ffprobe may be
	// missing on the host or the file may be unreadable.
	let details = $derived(file.details ?? null);

	// Measured from the video stream itself, not taken from the release name.
	let quality = $derived(details?.quality != null ? getQualityString(details.quality) : null);

	let sizeLabel = $derived(formatBytes(details?.size_bytes));
	let durationLabel = $derived(
		details?.duration_seconds != null && details.duration_seconds > 0
			? formatSecondsToOptimalUnit(details.duration_seconds)
			: null
	);
	let resolutionLabel = $derived(
		details?.width != null && details?.height != null
			? `${details.width} × ${details.height}`
			: null
	);
	let audioLabel = $derived(
		[details?.audio_codec, formatAudioChannels(details?.audio_channels)]
			.filter((part) => part != null && part !== '')
			.join(', ') || null
	);
</script>

<Dialog.Content class="w-full max-w-[500px] rounded-lg p-6 shadow-lg">
	<Dialog.Header class="min-w-0">
		<Dialog.Title class="mb-1 text-xl font-semibold">File details</Dialog.Title>
		<Dialog.Description class="font-mono text-sm break-all">
			{file.file_path || 'No file path recorded yet.'}
		</Dialog.Description>
	</Dialog.Header>

	{#if quality}
		<div class="flex flex-wrap items-center gap-2">
			<Badge variant="outline">
				<Film class="mr-1 size-3" />
				{quality}
			</Badge>
		</div>
	{/if}

	{#if file.exists_on_disk && details}
		<div class="grid grid-cols-2 gap-2">
			<TorrentStat icon={HardDrive} label="Size" value={sizeLabel ?? UNKNOWN} />
			<TorrentStat icon={Clock} label="Duration" value={durationLabel ?? UNKNOWN} />
			<TorrentStat icon={MonitorPlay} label="Resolution" value={resolutionLabel ?? UNKNOWN} />
			<TorrentStat icon={Package} label="Container" value={details.container ?? UNKNOWN} />
			<TorrentStat icon={Film} label="Video" value={details.video_codec ?? UNKNOWN} />
			<TorrentStat icon={AudioLines} label="Audio" value={audioLabel ?? UNKNOWN} />
		</div>

		<SubtitleTrackList subtitles={details.subtitles ?? []} />
	{:else}
		<EmptyState icon={FileQuestionMark} title="Not found on disk">
			No file was found at this path, so it could not be inspected. It may have been moved or
			deleted outside of MediaManager.
		</EmptyState>
	{/if}

	{#if file.file_path_suffix}
		<p class="text-xs text-muted-foreground">
			Version suffix: <span class="font-mono">{file.file_path_suffix}</span>
		</p>
	{/if}

	{#if user().is_superuser}
		<div class="flex flex-wrap gap-2 border-t pt-3 *:flex-1">
			<Button
				variant="outline"
				class="text-destructive hover:text-destructive"
				onclick={() => (deleteConfirmOpen = true)}
			>
				<Trash2 />
				Delete File
			</Button>
		</div>
	{/if}
</Dialog.Content>

<DeleteMediaFileDialog {file} bind:open={deleteConfirmOpen} {onDeleted} />
