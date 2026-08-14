<script lang="ts">
	import DownloadCard from '$lib/components/downloads/download-card.svelte';
	import * as Carousel from '$lib/components/ui/carousel/index.js';
	import { ResponsiveCarouselOpts } from '$lib/hooks/responsive-carousel-opts.svelte.js';
	import type { TorrentWithProgress } from '$lib/api/api';

	let { torrents }: { torrents: TorrentWithProgress[] } = $props();

	const carouselOpts = new ResponsiveCarouselOpts();
</script>

<Carousel.Root class="w-full md:px-12" opts={carouselOpts.opts}>
	<Carousel.Content>
		{#each torrents as torrent (torrent.id)}
			<Carousel.Item class="basis-4/5 sm:basis-1/2 lg:basis-1/3 xl:basis-1/4">
				<DownloadCard {torrent} />
			</Carousel.Item>
		{/each}
	</Carousel.Content>

	<Carousel.Previous class="left-0 hidden size-10 md:inline-flex [&_svg]:size-5" />
	<Carousel.Next class="right-0 hidden size-10 md:inline-flex [&_svg]:size-5" />
</Carousel.Root>
