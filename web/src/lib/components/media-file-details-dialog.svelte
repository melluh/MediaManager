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
	import Captions from '@lucide/svelte/icons/captions';
	import Clock from '@lucide/svelte/icons/clock';
	import FileQuestionMark from '@lucide/svelte/icons/file-question-mark';
	import FileText from '@lucide/svelte/icons/file-text';
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

	// Subtitle language/track fields ultimately come from a downloaded file's
	// own filename or embedded metadata - untrusted input. The backend already
	// sanitizes them, but they're still rendered as plain text interpolation
	// here (never `{@html}`) as defense in depth.
	let subtitles = $derived(details?.subtitles ?? []);

	type SubtitleFormat = { label: string; kind: 'text' | 'image' | null };

	// Embedded tracks report ffprobe's codec_name, sidecars their file
	// extension - both map onto the name people know the format by. Image
	// formats (ripped from Blu-ray/DVD) can't be restyled or searched without
	// OCR, which is worth knowing when a text track of the same language exists.
	const SUBTITLE_FORMATS: Record<string, SubtitleFormat> = {
		subrip: { label: 'SRT', kind: 'text' },
		srt: { label: 'SRT', kind: 'text' },
		ass: { label: 'ASS', kind: 'text' },
		ssa: { label: 'SSA', kind: 'text' },
		webvtt: { label: 'WebVTT', kind: 'text' },
		vtt: { label: 'WebVTT', kind: 'text' },
		mov_text: { label: 'MP4 text', kind: 'text' },
		text: { label: 'Text', kind: 'text' },
		microdvd: { label: 'MicroDVD', kind: 'text' },
		hdmv_pgs_subtitle: { label: 'PGS', kind: 'image' },
		dvd_subtitle: { label: 'VobSub', kind: 'image' },
		dvb_subtitle: { label: 'DVB', kind: 'image' },
		// A .sub file is either MicroDVD text or VobSub images - can't tell
		// from the extension alone.
		sub: { label: 'SUB', kind: null }
	};

	function subtitleFormat(codec: string | null | undefined): SubtitleFormat | null {
		if (!codec) return null;
		return SUBTITLE_FORMATS[codec.toLowerCase()] ?? { label: codec.toUpperCase(), kind: null };
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

		<section class="flex flex-col gap-2">
			<h3 class="flex items-center gap-2 text-sm font-medium">
				<Captions class="size-4 text-muted-foreground" />
				Subtitles
				{#if subtitles.length > 0}
					<span class="text-xs font-normal text-muted-foreground">{subtitles.length}</span>
				{/if}
			</h3>
			{#if subtitles.length === 0}
				<p class="rounded-lg border border-dashed px-3 py-2 text-xs text-muted-foreground">
					No embedded subtitle tracks or subtitle files next to this file.
				</p>
			{:else}
				<!-- Listed in file order (embedded streams first, then sidecars), matching
				     the track order a player shows. -->
				<ul class="max-h-64 divide-y overflow-y-auto rounded-lg border bg-muted/40">
					{#each subtitles as subtitle, i (i)}
						{@const format = subtitleFormat(subtitle.codec)}
						<li class="flex items-center justify-between gap-3 px-3 py-2">
							<div class="flex min-w-0 flex-wrap items-center gap-1.5">
								<span
									class="truncate text-sm font-medium"
									class:text-muted-foreground={subtitle.language.code === 'und'}
								>
									{subtitle.language.name}
								</span>
								{#if subtitle.forced}
									<Badge variant="secondary">Forced</Badge>
								{/if}
								{#if subtitle.hearing_impaired}
									<Badge variant="secondary" title="Subtitles for the deaf and hard of hearing">
										SDH
									</Badge>
								{/if}
							</div>
							<div class="flex shrink-0 items-center gap-2 text-xs text-muted-foreground">
								{#if format}
									<span
										class="flex items-center gap-1"
										title={format.kind ? `${format.kind}-based subtitles` : undefined}
									>
										<Badge variant="outline" class="font-mono">{format.label}</Badge>
										{#if format.kind}{format.kind}{/if}
									</span>
								{/if}
								{#if subtitle.source === 'embedded'}
									<span class="flex items-center gap-1" title="Stored inside the video file">
										<Package class="size-3" />
										Embedded
									</span>
								{:else}
									<span
										class="flex items-center gap-1"
										title="Separate subtitle file next to the video"
									>
										<FileText class="size-3" />
										External
									</span>
								{/if}
							</div>
						</li>
					{/each}
				</ul>
			{/if}
		</section>
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
