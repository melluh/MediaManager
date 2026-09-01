<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Badge, type BadgeVariant } from '$lib/components/ui/badge/index.js';
	import { CircularProgress } from '$lib/components/ui/circular-progress/index.js';
	import TorrentStat from '$lib/components/download-dialogs/torrent-stat.svelte';
	import { getDownloadStatusBadge } from '$lib/components/downloads/download-status.js';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import Globe from '@lucide/svelte/icons/globe';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Gauge from '@lucide/svelte/icons/gauge';
	import HardDrive from '@lucide/svelte/icons/hard-drive';
	import Film from '@lucide/svelte/icons/film';
	import Users from '@lucide/svelte/icons/users';
	import Clock from '@lucide/svelte/icons/clock';
	import ClockAlert from '@lucide/svelte/icons/clock-alert';
	import { resolve } from '$app/paths';
	import type { TorrentWithProgress } from '$lib/api/api';
	import {
		cn,
		formatBytes,
		formatDownloadSpeed,
		formatLastUpdated,
		formatSecondsToOptimalUnit,
		getTorrentQualityString
	} from '$lib/utils';

	const statusContainerClasses: Record<NonNullable<BadgeVariant>, string> = {
		default: 'border-primary/50 bg-primary/10 text-primary',
		secondary: 'border-muted-foreground/30 bg-muted text-muted-foreground',
		destructive: 'border-destructive/50 bg-destructive/10 text-destructive',
		outline: 'border-border bg-background text-foreground'
	};

	let { torrent }: { torrent: TorrentWithProgress } = $props();

	let progress = $derived(torrent.download_progress);
	let statusBadge = $derived(getDownloadStatusBadge(torrent));
	let waitingForImport = $derived(
		statusBadge.isFinished && !torrent.import_error && !torrent.imported
	);
	let downloadedLabel = $derived(formatBytes(progress?.downloaded_bytes));
	let totalLabel = $derived(formatBytes(progress?.total_bytes));
	let speedLabel = $derived(formatDownloadSpeed(progress?.download_speed_bytes_per_second));
	let etaLabel = $derived(
		progress?.eta_seconds != null ? formatSecondsToOptimalUnit(progress.eta_seconds) : undefined
	);
	let seedersLabel = $derived(progress?.seeders != null ? String(progress.seeders) : undefined);
	let leechersLabel = $derived(progress?.leechers != null ? String(progress.leechers) : undefined);
	let addedLabel = $derived(formatLastUpdated(torrent.initiated_at));
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
</script>

<Dialog.Content class="w-full max-w-[500px] rounded-lg p-6 shadow-lg">
	<Dialog.Header class="min-w-0">
		<Dialog.Title class="mb-1 text-xl font-semibold">
			{torrent.media?.name ?? torrent.title}
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
			<p class="text-xs font-normal">{torrent.import_error}</p>
		{/if}
	</div>

	{#if showLiveProgress}
		{#if progress}
			<div class="flex flex-col items-center gap-1 py-2">
				{#if waitingForImport}
					<ClockAlert class="h-[72px] w-[72px] text-muted-foreground" />
				{:else}
					<CircularProgress value={progress.progress} size={72} strokeWidth={6}>
						<span class="text-base font-semibold">{Math.round(progress.progress)}%</span>
					</CircularProgress>
				{/if}
				{#if waitingForImport}
					<p class="text-xs text-muted-foreground">Waiting for import to run</p>
				{:else if downloadedLabel && totalLabel}
					<p class="text-xs text-muted-foreground">{downloadedLabel} of {totalLabel}</p>
				{:else if totalLabel}
					<p class="text-xs text-muted-foreground">{totalLabel} total</p>
				{/if}
			</div>

			<div class="grid grid-cols-2 gap-2">
				<TorrentStat icon={Gauge} label="Speed" value={speedLabel ?? 'idle'} />
				<TorrentStat icon={Clock} label="ETA" value={etaLabel ?? 'unknown'} />
				<TorrentStat
					icon={Users}
					label="Peers"
					value={seedersLabel != null || leechersLabel != null
						? `${seedersLabel ?? '0'} seeders, ${leechersLabel ?? '0'} leechers`
						: 'unknown'}
				/>
			</div>
		{:else}
			<p class="text-sm text-muted-foreground">
				Live progress isn't available for this download client.
			</p>
		{/if}
	{/if}
</Dialog.Content>
