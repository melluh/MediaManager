<script lang="ts" module>
	import type { PublicEpisodeFile, PublicMovieFile } from '$lib/api/api';

	/**
	 * Movie and episode files share the `PublicMediaFile` base, so anything that
	 * only touches the shared fields can accept either.
	 */
	export type MediaFile = PublicMovieFile | PublicEpisodeFile;
</script>

<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import TorrentStat from '$lib/components/download-dialogs/torrent-stat.svelte';
	import AudioLines from '@lucide/svelte/icons/audio-lines';
	import Clock from '@lucide/svelte/icons/clock';
	import FileQuestionMark from '@lucide/svelte/icons/file-question-mark';
	import Film from '@lucide/svelte/icons/film';
	import HardDrive from '@lucide/svelte/icons/hard-drive';
	import MonitorPlay from '@lucide/svelte/icons/monitor-play';
	import Package from '@lucide/svelte/icons/package';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { formatBytes, formatSecondsToOptimalUnit, getTorrentQualityString } from '$lib/utils';

	let { file }: { file: MediaFile } = $props();

	const UNKNOWN = 'unknown';

	// `details` is only populated when the file was actually found and probed;
	// every field inside it is independently optional, because ffprobe may be
	// missing on the host or the file may be unreadable.
	let details = $derived(file.details ?? null);

	let claimedQuality = $derived(getTorrentQualityString(file.quality));
	let probedQuality = $derived(
		details?.probed_quality != null ? getTorrentQualityString(details.probed_quality) : null
	);
	// `quality` is what the release claimed, `probed_quality` is what the file
	// actually is - a mislabelled release is the thing this dialog exists to show.
	let qualityMismatch = $derived(
		details?.probed_quality != null && details.probed_quality !== file.quality
	);

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

	function formatAudioChannels(channels: number | null | undefined): string | null {
		if (channels == null || channels <= 0) return null;
		const named: Record<number, string> = { 1: 'mono', 2: 'stereo', 6: '5.1', 8: '7.1' };
		return named[channels] ?? `${channels} channels`;
	}
</script>

<Dialog.Content class="w-full max-w-[500px] rounded-lg p-6 shadow-lg">
	<Dialog.Header class="min-w-0">
		<Dialog.Title class="mb-1 text-xl font-semibold">File details</Dialog.Title>
		<Dialog.Description class="font-mono text-sm break-all">
			{file.file_path || 'No file path recorded yet.'}
		</Dialog.Description>
	</Dialog.Header>

	{#if qualityMismatch}
		<div
			class="flex items-start gap-2 rounded-lg border border-destructive/50 bg-destructive/10 px-3 py-2 text-destructive"
		>
			<TriangleAlert class="mt-0.5 size-4 shrink-0" />
			<div class="min-w-0">
				<p class="text-sm font-medium">Quality mismatch</p>
				<p class="text-xs">
					The release claims {claimedQuality}, but the file measures {probedQuality}.
				</p>
			</div>
		</div>
	{:else}
		<div class="flex flex-wrap items-center gap-2">
			<Badge variant="outline">
				<Film class="mr-1 size-3" />
				{claimedQuality}
			</Badge>
			{#if probedQuality}
				<span class="text-xs text-muted-foreground">confirmed by probing the file</span>
			{/if}
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
	{:else}
		<div
			class="flex flex-col items-center gap-1 rounded-lg border border-dashed px-3 py-6 text-center"
		>
			<FileQuestionMark class="size-8 text-muted-foreground" />
			<p class="text-sm font-medium">Not found on disk</p>
			<p class="text-xs text-muted-foreground">
				{#if file.downloaded}
					No file was found at this path, so it could not be inspected. It may have been moved or
					deleted outside of MediaManager.
				{:else}
					This version is still downloading, so there is nothing to inspect yet.
				{/if}
			</p>
		</div>
	{/if}

	{#if file.file_path_suffix}
		<p class="text-xs text-muted-foreground">
			Version suffix: <span class="font-mono">{file.file_path_suffix}</span>
		</p>
	{/if}
</Dialog.Content>
