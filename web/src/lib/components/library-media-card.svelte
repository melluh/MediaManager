<script lang="ts">
	import { resolve } from '$app/paths';
	import MediaCard from '$lib/components/media-card.svelte';
	import MediaImage from '$lib/components/media-image.svelte';
	import ImageOff from '@lucide/svelte/icons/image-off';
	import type { MovieListItem, SearchResult, ShowSummary } from '$lib/api/api';
	import type { Snippet } from 'svelte';

	let posterLoaded = $state(false);
	let {
		media,
		isShow,
		indicators
	}: {
		media: MovieListItem | ShowSummary | SearchResult;
		isShow: boolean;
		indicators?: Snippet;
	} = $props();

	let hasPoster = $derived(!!media.images?.poster);
	let slugOrId = $derived(media.slug ?? media.id ?? '');
	let href = $derived(
		resolve(
			isShow ? '/dashboard/tv/[showId]' : '/dashboard/movies/[movieId]',
			isShow ? { showId: slugOrId } : { movieId: slugOrId }
		)
	);
</script>

<MediaCard
	name={media.name}
	year={media.year}
	runtime={media.runtime}
	genres={media.genres}
	{posterLoaded}
	{hasPoster}
	{href}
	{indicators}
>
	{#snippet poster()}
		{#if hasPoster}
			<MediaImage {media} className="h-full w-full object-cover" bind:loaded={posterLoaded} />
		{:else}
			<div class="flex h-full w-full items-center justify-center bg-muted">
				<ImageOff class="h-12 w-12 text-gray-400" />
			</div>
		{/if}
	{/snippet}
</MediaCard>
