<script lang="ts">
	import AddMediaCard from '$lib/components/add-media-card.svelte';
	import MediaCardSkeleton from '$lib/components/media-card-skeleton.svelte';
	import * as Carousel from '$lib/components/ui/carousel/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import { ResponsiveCarouselOpts } from '$lib/hooks/responsive-carousel-opts.svelte.js';
	import AlertCircleIcon from '@lucide/svelte/icons/alert-circle';
	import type { MetaDataProviderSearchResult } from '$lib/api/api';

	let {
		media,
		isShow,
		isLoading,
		isError = false,
		caption
	}: {
		media: MetaDataProviderSearchResult[];
		isShow: boolean;
		isLoading: boolean;
		isError?: boolean;
		/** A line shown under an item's card, e.g. why it's recommended. */
		caption?: (item: MetaDataProviderSearchResult) => string | undefined;
	} = $props();

	const carouselOpts = new ResponsiveCarouselOpts();
</script>

<Carousel.Root class="w-full lg:pointer-fine:px-12" opts={carouselOpts.opts}>
	<Carousel.Content class={isError ? 'pointer-events-none blur-xs' : ''}>
		{#if isLoading || isError}
			{#each { length: 6 }}
				<Carousel.Item class="basis-2/5 md:basis-2/7 lg:basis-2/11 lg:pointer-fine:basis-1/6">
					<MediaCardSkeleton pulsating={!isError} />
				</Carousel.Item>
			{/each}
		{:else}
			{#each media as mediaItem (mediaItem.external_id)}
				<Carousel.Item class="basis-2/5 md:basis-2/7 lg:basis-2/11 lg:pointer-fine:basis-1/6">
					<AddMediaCard {isShow} result={mediaItem} />
					{@const itemCaption = caption?.(mediaItem)}
					{#if itemCaption}
						<p class="mt-1.5 line-clamp-2 text-xs text-muted-foreground" title={itemCaption}>
							{itemCaption}
						</p>
					{/if}
				</Carousel.Item>
			{/each}
		{/if}
	</Carousel.Content>

	{#if isError}
		<div class="pointer-events-none absolute inset-0 flex items-center justify-center p-4">
			<Alert.Root variant="destructive" class="w-auto max-w-md bg-background/90 shadow-sm">
				<AlertCircleIcon class="size-4" />
				<Alert.Title>Failed to load recommendations</Alert.Title>
				<Alert.Description>
					Could not reach the metadata provider. Please try again later.
				</Alert.Description>
			</Alert.Root>
		</div>
	{:else}
		<Carousel.Previous class="left-0 hidden size-10 lg:pointer-fine:inline-flex [&_svg]:size-5" />
		<Carousel.Next class="right-0 hidden size-10 lg:pointer-fine:inline-flex [&_svg]:size-5" />
	{/if}
</Carousel.Root>
