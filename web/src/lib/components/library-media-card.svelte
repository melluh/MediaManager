<script lang="ts">
	import { resolve } from '$app/paths';
	import MediaCard from '$lib/components/media-card.svelte';
	import MediaPicture from '$lib/components/media-picture.svelte';
	import type { Movie, SearchResult, ShowSummary } from '$lib/api/api';
	import type { Snippet } from 'svelte';

	let posterLoaded = $state(false);
	let {
		media,
		isShow,
		indicators
	}: {
		media: Movie | ShowSummary | SearchResult;
		isShow: boolean;
		indicators?: Snippet;
	} = $props();

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
	{href}
	{indicators}
>
	{#snippet poster()}
		<MediaPicture {media} className="h-full w-full object-cover" bind:loaded={posterLoaded} />
	{/snippet}
</MediaCard>
