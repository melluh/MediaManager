<script lang="ts">
	import AddMediaCard from '$lib/components/add-media-card.svelte';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Carousel from '$lib/components/ui/carousel/index.js';
	import { useSidebar } from '$lib/components/ui/sidebar/index.js';
	import type { MetaDataProviderSearchResult } from '$lib/api/api';

	let {
		media,
		isShow,
		isLoading
	}: {
		media: MetaDataProviderSearchResult[];
		isShow: boolean;
		isLoading: boolean;
	} = $props();

	// Reuses the sidebar's mobile-detection instance (this carousel only ever
	// renders inside the dashboard's Sidebar.Provider) rather than opening a
	// second matchMedia listener for the same breakpoint.
	const sidebar = useSidebar();
	// On mobile, scroll freely instead of snapping to slide boundaries -
	// align only controls where snap points land, so it can't disable
	// snapping by itself.
	let opts = $derived(sidebar.isMobile ? { dragFree: true } : ({ align: 'start' } as const));
</script>

<Carousel.Root class="w-full md:px-12" {opts}>
	<Carousel.Content>
		{#if isLoading}
			{#each { length: 5 }}
				<Carousel.Item class="basis-2/5 lg:basis-1/5">
					<Skeleton class="aspect-2/3 w-full" />
				</Carousel.Item>
			{/each}
		{:else}
			{#each media as mediaItem (mediaItem.external_id)}
				<Carousel.Item class="basis-2/5 lg:basis-1/5">
					<AddMediaCard {isShow} result={mediaItem} />
				</Carousel.Item>
			{/each}
		{/if}
	</Carousel.Content>

	<Carousel.Previous class="left-0 hidden size-10 md:inline-flex [&_svg]:size-5" />
	<Carousel.Next class="right-0 hidden size-10 md:inline-flex [&_svg]:size-5" />
</Carousel.Root>
