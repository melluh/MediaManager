<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Badge, type BadgeVariant } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import CopyButton from '$lib/components/copy-button.svelte';
	import CancelDownloadDialog from '$lib/components/downloads/cancel-download-dialog.svelte';
	import DownloadProgressPanel from '$lib/components/downloads/download-progress-panel.svelte';
	import ImportFilePicker from '$lib/components/downloads/import-file-picker.svelte';
	import { getDownloadStatusBadge } from '$lib/components/downloads/download-status.js';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import Globe from '@lucide/svelte/icons/globe';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import HardDrive from '@lucide/svelte/icons/hard-drive';
	import Film from '@lucide/svelte/icons/film';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import { resolve } from '$app/paths';
	import type { TorrentWithProgress } from '$lib/api/api';
	import {
		cn,
		formatBytes,
		formatLastUpdated,
		formatTorrentSeasonEpisodeRange,
		getTorrentQualityString
	} from '$lib/utils';

	const statusContainerClasses: Record<NonNullable<BadgeVariant>, string> = {
		default: 'border-primary/50 bg-primary/10 text-primary',
		secondary: 'border-muted-foreground/30 bg-muted text-muted-foreground',
		destructive: 'border-destructive/50 bg-destructive/10 text-destructive',
		outline: 'border-border bg-background text-foreground'
	};

	let { torrent }: { torrent: TorrentWithProgress } = $props();

	let statusBadge = $derived(getDownloadStatusBadge(torrent));
	let waitingForImport = $derived(
		statusBadge.isFinished && !torrent.import_error && !torrent.imported
	);
	let totalLabel = $derived(formatBytes(torrent.download_progress?.total_bytes));
	let addedLabel = $derived(formatLastUpdated(torrent.initiated_at));
	let seasonEpisodeLabel = $derived(
		formatTorrentSeasonEpisodeRange(torrent.seasons, torrent.episodes)
	);
	let showLiveProgress = $derived(
		statusBadge.variant !== 'destructive' && statusBadge.variant !== 'default'
	);
	let mediaHref = $derived.by(() => {
		if (!torrent.media) return undefined;
		const slugOrId = torrent.media.slug ?? torrent.media.id;
		return torrent.media.is_show
			? resolve('/dashboard/tv/[showId]', { showId: slugOrId })
			: resolve('/dashboard/movies/[movieId]', { movieId: slugOrId });
	});

	// Movie-only for now: TV torrents don't have this failure mode.
	let canResolveMultipleVideoFiles = $derived(
		torrent.import_error_kind === 'multiple_video_files' &&
			torrent.media != null &&
			!torrent.media.is_show
	);

	let cancelConfirmOpen = $state(false);
</script>

<Dialog.Content class="w-full max-w-[500px] rounded-lg p-6 shadow-lg">
	<Dialog.Header class="min-w-0">
		<Dialog.Title class="mb-1 text-xl font-semibold">
			{torrent.media?.name ?? torrent.title}{#if seasonEpisodeLabel}
				<span class="text-muted-foreground">&nbsp;{seasonEpisodeLabel}</span>{/if}
		</Dialog.Title>
		<Dialog.Description class="font-mono text-sm">
			{torrent.title}
		</Dialog.Description>
	</Dialog.Header>

	<div class="flex flex-wrap items-center gap-2">
		<Badge variant="outline">
			<Film class="mr-1 size-3" />
			{getTorrentQualityString(torrent.quality)}
		</Badge>
		{#if totalLabel}
			<Badge variant="outline">
				<HardDrive class="mr-1 size-3" />
				{totalLabel}
			</Badge>
		{/if}
		{#if mediaHref}
			<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- href is built from resolve() in mediaHref -->
			<a href={mediaHref} class="ml-auto text-sm text-primary hover:underline">View media</a>
		{/if}
	</div>

	<div class="flex flex-col gap-1">
		<p class="flex items-center gap-1.5 text-xs text-muted-foreground">
			<Globe class="size-3.5 shrink-0" /><span
				>{torrent.usenet ? 'Usenet' : 'Torrent'}
				{#if torrent.indexer}
					from
					{#if torrent.comments}<a
							href={torrent.comments}
							target="_blank"
							rel="noopener noreferrer external"
							class="inline-flex items-center underline hover:text-foreground"
							>{torrent.indexer}<ExternalLink class="ml-0.5 size-3" /></a
						>{:else}{torrent.indexer}{/if}
				{/if}</span
			>
		</p>

		{#if addedLabel}
			<p class="flex items-center gap-1.5 text-xs text-muted-foreground">
				<CalendarClock class="size-3.5" />
				Added {addedLabel}
			</p>
		{/if}
	</div>

	<hr />

	<p class="text-sm font-medium">Status</p>

	<div
		class={cn(
			'flex flex-col gap-1 rounded-lg border px-3 py-2 text-sm font-medium',
			statusContainerClasses[statusBadge.variant ?? 'default']
		)}
	>
		<div class="flex items-center gap-2">
			<statusBadge.icon class="size-4 shrink-0" />
			{statusBadge.label}
		</div>
		{#if torrent.import_error}
			<!-- The import error is a raw exception message, so it can be arbitrarily
			     long. It is clamped here and copyable in full. -->
			<div class="group/error flex items-start gap-2">
				<p class="line-clamp-3 min-w-0 flex-1 text-xs font-normal break-words">
					{torrent.import_error}
				</p>
				<CopyButton
					text={torrent.import_error}
					class="opacity-0 transition-opacity group-hover/error:opacity-100 focus-visible:opacity-100"
				/>
			</div>
		{/if}
	</div>

	{#if showLiveProgress}
		<DownloadProgressPanel progress={torrent.download_progress} {waitingForImport} />
	{/if}

	{#if canResolveMultipleVideoFiles}
		<ImportFilePicker movieId={torrent.media!.id} torrentId={torrent.id!} />
	{/if}

	<div class="border-t pt-3">
		<Button
			variant="outline"
			class="w-full text-destructive hover:text-destructive"
			onclick={() => (cancelConfirmOpen = true)}
		>
			<CircleX />
			Cancel Download
		</Button>
	</div>
</Dialog.Content>

<CancelDownloadDialog {torrent} bind:open={cancelConfirmOpen} />
