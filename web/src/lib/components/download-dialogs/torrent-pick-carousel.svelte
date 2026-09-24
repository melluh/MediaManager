<script lang="ts">
	import * as Carousel from '$lib/components/ui/carousel';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import LoadingOverlay from '$lib/components/loading-overlay.svelte';
	import TorrentPickCard from '$lib/components/download-dialogs/torrent-pick-card.svelte';
	import type { groupIntoSlots } from '$lib/components/download-dialogs/torrent-grouping';

	let {
		picks,
		loading,
		selectedResultId,
		onSelect
	}: {
		picks: ReturnType<typeof groupIntoSlots>['allPicks'];
		/** Shows placeholder cards under a "searching" overlay instead of `picks`. */
		loading: boolean;
		selectedResultId: string | null;
		onSelect: (resultId: string | null) => void;
	} = $props();
</script>

<Carousel.Root class="mx-8 my-4 min-w-0">
	<Carousel.Content>
		{#if loading}
			{#each { length: 3 }}
				<Carousel.Item class="basis-full sm:basis-1/2 lg:basis-1/3">
					<Skeleton class="h-95 w-full rounded-lg" />
				</Carousel.Item>
			{/each}
		{:else}
			{#each picks as pick (pick.slotName)}
				<Carousel.Item class="basis-full sm:basis-1/2 lg:basis-1/3">
					<TorrentPickCard
						result={pick.result}
						slotLabel={pick.slotLabel}
						selected={selectedResultId === pick.result.id}
						onSelect={() => onSelect(pick.result.id ?? null)}
					/>
				</Carousel.Item>
			{/each}
		{/if}
	</Carousel.Content>
	<Carousel.Previous />
	<Carousel.Next />
	{#if loading}
		<LoadingOverlay message="Searching for torrents..." />
	{/if}
</Carousel.Root>
