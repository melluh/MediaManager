<script lang="ts">
	import MovieDetail from '$lib/components/movie-detail.svelte';
	import PageLoading from '$lib/components/page-loading.svelte';
	import PageLoadError from '$lib/components/page-load-error.svelte';
	import SeededMediaDetail from '$lib/components/seeded-media-detail.svelte';
	import { resolve } from '$app/paths';
	import { getFullyQualifiedMediaName } from '$lib/utils';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

{#await data.details}
	{#if data.seed}
		<SeededMediaDetail
			media={data.seed}
			isShow={false}
			crumbs={[
				{ label: 'Movies', href: resolve('/dashboard/movies', {}) },
				{ label: getFullyQualifiedMediaName(data.seed) }
			]}
			message="Loading movie…"
		/>
	{:else}
		<PageLoading message="Loading movie…" />
	{/if}
{:then { movie, movieFiles }}
	<MovieDetail {movie} {movieFiles} />
{:catch error}
	<PageLoadError title="Movie unavailable" message={error.message} />
{/await}
