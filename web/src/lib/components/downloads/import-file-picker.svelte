<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import Circle from '@lucide/svelte/icons/circle';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import { toast } from 'svelte-sonner';
	import client from '$lib/api';
	import type { TorrentImportCandidate } from '$lib/api/api';
	import { cn, formatBytes, getQualityString } from '$lib/utils';

	// Resolves a movie download whose import failed because it contained more
	// than one video file, by letting the user pick the one to import.
	let {
		movieId,
		torrentId,
		onChange
	}: {
		movieId: string;
		torrentId: string;
		/** Called after the download changed, so the owner can refresh it. */
		onChange?: () => void;
	} = $props();

	let candidates = $state<TorrentImportCandidate[] | null>(null);
	let loading = $state(false);
	let loadError = $state<string | null>(null);
	let selectedPath = $state<string | null>(null);
	let resolving = $state(false);

	$effect(() => {
		fetchCandidates(movieId, torrentId);
	});

	async function fetchCandidates(movieId: string, torrentId: string) {
		loading = true;
		loadError = null;

		const { data, error } = await client.GET(
			'/api/v1/movies/{movie_id}/torrents/{torrent_id}/import-candidates',
			{ params: { path: { movie_id: movieId, torrent_id: torrentId } } }
		);

		loading = false;
		if (error) {
			loadError = 'Failed to load the files found in this download.';
			return;
		}
		candidates = data;
		selectedPath = data[0]?.relative_path ?? null;
	}

	async function resolveImport() {
		if (!selectedPath) return;

		resolving = true;
		const { error, response } = await client.POST(
			'/api/v1/movies/{movie_id}/torrents/{torrent_id}/import',
			{
				params: {
					path: { movie_id: movieId, torrent_id: torrentId },
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
			onChange?.();
			return;
		}

		toast.success('Import resolved successfully.');
		onChange?.();
	}

	function formatDuration(seconds: number | null | undefined): string {
		if (seconds == null || seconds <= 0) return 'unknown length';
		const hours = Math.floor(seconds / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
	}
</script>

<div class="space-y-2 border-t pt-3">
	<p class="text-sm font-medium">Multiple video files were found — pick one to import:</p>
	{#if loading}
		<div class="flex items-center justify-center py-4">
			<Spinner class="size-6" />
		</div>
	{:else if loadError}
		<p class="text-xs text-destructive">{loadError}</p>
	{:else if candidates && candidates.length === 0}
		<p class="text-xs text-muted-foreground">
			No video files were found anymore in this download's directory.
		</p>
	{:else if candidates}
		<div class="max-h-[220px] space-y-1 overflow-y-auto pr-1">
			{#each candidates as candidate (candidate.relative_path)}
				{@const selected = selectedPath === candidate.relative_path}
				<button
					type="button"
					class={cn(
						'flex w-full items-start gap-2 rounded-md border p-2 text-left text-xs transition-colors hover:bg-muted',
						selected && 'border-primary bg-muted'
					)}
					onclick={() => (selectedPath = candidate.relative_path)}
				>
					{#if selected}
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
							<span>{getQualityString(candidate.probed_quality)}</span>
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
