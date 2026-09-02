<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Badge, type BadgeVariant } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { CircularProgress } from '$lib/components/ui/circular-progress/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import TorrentStat from '$lib/components/download-dialogs/torrent-stat.svelte';
	import { getDownloadStatusBadge } from '$lib/components/downloads/download-status.js';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import Globe from '@lucide/svelte/icons/globe';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Circle from '@lucide/svelte/icons/circle';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import Gauge from '@lucide/svelte/icons/gauge';
	import HardDrive from '@lucide/svelte/icons/hard-drive';
	import Film from '@lucide/svelte/icons/film';
	import Users from '@lucide/svelte/icons/users';
	import Clock from '@lucide/svelte/icons/clock';
	import ClockAlert from '@lucide/svelte/icons/clock-alert';
	import { resolve } from '$app/paths';
	import { invalidateAll } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import client from '$lib/api';
	import type { TorrentImportCandidate, TorrentWithProgress } from '$lib/api/api';
	import {
		cn,
		formatBytes,
		formatDownloadSpeed,
		formatLastUpdated,
		formatSecondsToOptimalUnit,
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

	let candidates = $state<TorrentImportCandidate[] | null>(null);
	let candidatesLoading = $state(false);
	let candidatesError = $state<string | null>(null);
	let candidatesFetchedForTorrentId = $state<string | null>(null);
	let selectedPath = $state<string | null>(null);
	let resolving = $state(false);

	$effect(() => {
		if (!canResolveMultipleVideoFiles) return;
		if (candidatesFetchedForTorrentId === torrent.id) return;
		fetchCandidates();
	});

	async function fetchCandidates() {
		const movieId = torrent.media?.id;
		if (!movieId) return;

		candidatesLoading = true;
		candidatesError = null;
		candidatesFetchedForTorrentId = torrent.id!;

		const { data, error } = await client.GET(
			'/api/v1/movies/{movie_id}/torrents/{torrent_id}/import-candidates',
			{ params: { path: { movie_id: movieId, torrent_id: torrent.id! } } }
		);

		candidatesLoading = false;
		if (error) {
			candidatesError = 'Failed to load the files found in this download.';
			return;
		}
		candidates = data;
		selectedPath = data[0]?.relative_path ?? null;
	}

	async function resolveImport() {
		const movieId = torrent.media?.id;
		if (!movieId || !selectedPath) return;

		resolving = true;
		const { error, response } = await client.POST(
			'/api/v1/movies/{movie_id}/torrents/{torrent_id}/import',
			{
				params: {
					path: { movie_id: movieId, torrent_id: torrent.id! },
					query: { relative_path: selectedPath }
				}
			}
		);
		resolving = false;

		if (error) {
			if (response.status === 409) {
				toast.info('This download was already resolved.');
			} else {
				toast.error('Failed to import the selected file.');
			}
			await invalidateAll();
			return;
		}

		toast.success('Import resolved successfully.');
		await invalidateAll();
	}

	function formatDuration(seconds: number | null | undefined): string {
		if (seconds == null || seconds <= 0) return 'unknown length';
		const hours = Math.floor(seconds / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
	}
</script>

<Dialog.Content class="w-full max-w-[500px] rounded-lg p-6 shadow-lg">
	<Dialog.Header class="min-w-0">
		<Dialog.Title class="mb-1 text-xl font-semibold">
			{torrent.media?.name ?? torrent.title}{#if seasonEpisodeLabel}
				<span class="text-muted-foreground">({seasonEpisodeLabel})</span>
			{/if}
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

	{#if canResolveMultipleVideoFiles}
		<div class="space-y-2 border-t pt-3">
			<p class="text-sm font-medium">Multiple video files were found — pick one to import:</p>
			{#if candidatesLoading}
				<div class="flex items-center justify-center py-4">
					<Spinner class="size-6" />
				</div>
			{:else if candidatesError}
				<p class="text-xs text-destructive">{candidatesError}</p>
			{:else if candidates && candidates.length === 0}
				<p class="text-xs text-muted-foreground">
					No video files were found anymore in this download's directory.
				</p>
			{:else if candidates}
				<div class="max-h-[220px] space-y-1 overflow-y-auto pr-1">
					{#each candidates as candidate (candidate.relative_path)}
						<button
							type="button"
							class={cn(
								'flex w-full items-start gap-2 rounded-md border p-2 text-left text-xs transition-colors hover:bg-muted',
								selectedPath === candidate.relative_path && 'border-primary bg-muted'
							)}
							onclick={() => (selectedPath = candidate.relative_path)}
						>
							{#if selectedPath === candidate.relative_path}
								<CircleCheck class="mt-0.5 size-3.5 shrink-0 text-primary" />
							{:else}
								<Circle class="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
							{/if}
							<span class="min-w-0 flex-1 space-y-0.5">
								<span class="block truncate font-medium" title={candidate.relative_path}>
									{candidate.file_name}
								</span>
								<span class="flex flex-wrap items-center gap-x-1.5 text-muted-foreground">
									<span>{formatBytes(candidate.size_bytes) ?? 'unknown size'}</span>
									<span>&middot;</span>
									<span>{getTorrentQualityString(candidate.quality)}</span>
									<span>&middot;</span>
									<span>{formatDuration(candidate.duration_seconds)}</span>
								</span>
							</span>
						</button>
					{/each}
				</div>
				<Button class="w-full" disabled={!selectedPath || resolving} onclick={resolveImport}>
					{#if resolving}
						<Spinner class="mr-1 size-4" />
					{/if}
					Import selected file
				</Button>
			{/if}
		</div>
	{/if}
</Dialog.Content>
