<script lang="ts">
	import { CircularProgress } from '$lib/components/ui/circular-progress/index.js';
	import TorrentStat from '$lib/components/download-dialogs/torrent-stat.svelte';
	import ClockAlert from '@lucide/svelte/icons/clock-alert';
	import Clock from '@lucide/svelte/icons/clock';
	import Gauge from '@lucide/svelte/icons/gauge';
	import Users from '@lucide/svelte/icons/users';
	import type { DownloadProgress } from '$lib/api/api';
	import { formatBytes, formatDownloadSpeed, formatSecondsToOptimalUnit } from '$lib/utils';

	let {
		progress,
		waitingForImport
	}: {
		progress: DownloadProgress | null | undefined;
		/** The download finished but hasn't been imported yet. */
		waitingForImport: boolean;
	} = $props();

	let downloadedLabel = $derived(formatBytes(progress?.downloaded_bytes));
	let totalLabel = $derived(formatBytes(progress?.total_bytes));
	let speedLabel = $derived(formatDownloadSpeed(progress?.download_speed_bytes_per_second));
	let etaLabel = $derived(
		progress?.eta_seconds != null ? formatSecondsToOptimalUnit(progress.eta_seconds) : undefined
	);
	let peersLabel = $derived(
		progress?.seeders != null || progress?.leechers != null
			? `${progress?.seeders ?? 0} seeders, ${progress?.leechers ?? 0} leechers`
			: 'unknown'
	);
</script>

{#if progress}
	<div class="flex flex-col items-center gap-1 py-2">
		{#if waitingForImport}
			<ClockAlert class="h-[72px] w-[72px] text-muted-foreground" />
			<p class="text-xs text-muted-foreground">Waiting for import to run</p>
		{:else}
			<CircularProgress value={progress.progress} size={72} strokeWidth={6}>
				<span class="text-base font-semibold">{Math.round(progress.progress)}%</span>
			</CircularProgress>
			{#if downloadedLabel && totalLabel}
				<p class="text-xs text-muted-foreground">{downloadedLabel} of {totalLabel}</p>
			{:else if totalLabel}
				<p class="text-xs text-muted-foreground">{totalLabel} total</p>
			{/if}
		{/if}
	</div>

	<div class="grid grid-cols-2 gap-2">
		<TorrentStat icon={Gauge} label="Speed" value={speedLabel ?? 'idle'} />
		<TorrentStat icon={Clock} label="ETA" value={etaLabel ?? 'unknown'} />
		<TorrentStat icon={Users} label="Peers" value={peersLabel} />
	</div>
{:else}
	<p class="text-sm text-muted-foreground">
		Live progress isn't available for this download client.
	</p>
{/if}
