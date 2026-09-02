<script lang="ts">
	import MovieDetail from '$lib/components/movie-detail.svelte';
	import PageLoading from '$lib/components/page-loading.svelte';
	import PageLoadError from '$lib/components/page-load-error.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

{#await data.details}
	<PageLoading message="Loading movie…" />
{:then { movie, movieFiles }}
	<MovieDetail {movie} {movieFiles} />
{:catch error}
	<PageLoadError title="Movie unavailable" message={error.message} />
{/await}
