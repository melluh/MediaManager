<script lang="ts">
	import QualitySelector from './quality-selector.svelte';
	import { Spinner } from '$lib/components/ui/spinner';
	import { ExternalLink } from 'lucide-svelte';
	import type { MediaQuality, SelectedTorrents } from './types';

	let {
		selectedQuality = $bindable(),
		torrentSearchState = 'idle',
		selectedTorrents
	}: {
		selectedQuality: MediaQuality | undefined;
		torrentSearchState?: 'idle' | 'loading' | 'done' | 'error';
		selectedTorrents?: SelectedTorrents;
	} = $props();

	let selectedTorrent = $derived(selectedQuality ? selectedTorrents?.[selectedQuality] : undefined);
</script>

<div class="flex h-full flex-col gap-4 overflow-y-auto px-6 pb-6">
	<div>
		<h3 class="text-base font-semibold">Select a quality</h3>
	</div>
	{#if torrentSearchState === 'loading'}
		<div class="flex flex-1 flex-col items-center justify-center gap-2 py-8 text-muted-foreground">
			<Spinner class="size-6" />
			<span class="text-sm">Searching for torrents...</span>
		</div>
	{:else}
		<QualitySelector bind:selectedQuality {selectedTorrents} />
		{#if selectedTorrent}
			<p class="text-sm text-muted-foreground">
				Torrent from
				{#if selectedTorrent.comments}
					<!-- eslint-disable svelte/no-navigation-without-resolve -->
					<a
						href={selectedTorrent.comments}
						target="_blank"
						rel="noopener noreferrer"
						class="inline-flex items-center gap-1 font-medium text-foreground underline decoration-dotted underline-offset-4"
					>
						{selectedTorrent.indexer ?? 'Unknown'}
						<ExternalLink class="size-3.5" />
					</a>
					<!-- eslint-enable svelte/no-navigation-without-resolve -->
				{:else}
					<span class="font-medium text-foreground">{selectedTorrent.indexer ?? 'Unknown'}</span>
				{/if}
				<span aria-hidden="true">&middot;</span>
				{selectedTorrent.seeders}
				{selectedTorrent.seeders === 1 ? 'seeder' : 'seeders'}
			</p>
		{/if}
	{/if}
</div>
