<script lang="ts">
	import { getContext } from 'svelte';
	import MediaHeroHeader from '$lib/components/media-hero-header.svelte';
	import PageLoading from '$lib/components/page-loading.svelte';
	import type { MovieListItem, ShowSummary } from '$lib/api/api';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';

	// Stand-in for a detail page while its full object loads: the hero is
	// painted from the library list item, the rest waits on the real fetch.
	let {
		media,
		isShow,
		crumbs,
		message
	}: {
		media: MovieListItem | ShowSummary;
		isShow: boolean;
		crumbs: Crumb[];
		message: string;
	} = $props();

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	$effect(() => {
		setCrumbs(crumbs);
	});
</script>

<MediaHeroHeader {media} {isShow}>
	<PageLoading {message} />
</MediaHeroHeader>
