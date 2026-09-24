<script lang="ts">
	import MovieDetail from '$lib/components/movie-detail.svelte';
	import PageLoading from '$lib/components/page-loading.svelte';
	import PageLoadError from '$lib/components/page-load-error.svelte';
	import SeededMediaDetail from '$lib/components/seeded-media-detail.svelte';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { Resolved } from '$lib/hooks/resolved.svelte';
	import { getFullyQualifiedMediaName } from '$lib/utils';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	// Resolved into local state rather than awaited in the markup, so a refresh
	// of the same movie (e.g. after an import finishes) updates in place instead
	// of remounting the page. Navigating to another movie reloads.
	const details = new Resolved(() => data.details, { key: () => page.params.movieId });
</script>

{#if details.status === 'error'}
	<PageLoadError
		title="Movie unavailable"
		message={details.error instanceof Error ? details.error.message : String(details.error)}
	/>
{:else if details.status === 'loading' && data.seed}
	<SeededMediaDetail
		media={data.seed}
		isShow={false}
		crumbs={[
			{ label: 'Movies', href: resolve('/dashboard/movies', {}) },
			{ label: getFullyQualifiedMediaName(data.seed) }
		]}
		message="Loading movie…"
	/>
{:else if details.status === 'loading'}
	<PageLoading message="Loading movie…" />
{:else}
	<MovieDetail movie={details.value!.movie} movieFiles={details.value!.movieFiles} />
{/if}
