<script lang="ts">
	import AddMediaCard from '$lib/components/add-media-card.svelte';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Carousel from '$lib/components/ui/carousel/index.js';
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
</script>

<Carousel.Root class="w-full px-12" opts={{ align: 'start' }}>
	<Carousel.Content>
		{#if isLoading}
			{#each { length: 4 }}
				<Carousel.Item class="sm:basis-full md:basis-1/2 lg:basis-1/4">
					<Skeleton class="h-[70vh] w-full" />
				</Carousel.Item>
			{/each}
		{:else}
			{#each media as mediaItem (mediaItem.external_id)}
				<Carousel.Item class="sm:basis-full md:basis-1/2 lg:basis-1/4">
					<AddMediaCard {isShow} result={mediaItem} />
				</Carousel.Item>
			{/each}
		{/if}
	</Carousel.Content>
	<Carousel.Previous class="left-0 size-10 [&_svg]:size-5" />
	<Carousel.Next class="right-0 size-10 [&_svg]:size-5" />
</Carousel.Root>
