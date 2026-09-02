<script lang="ts">
	import SeasonDetail from '$lib/components/season-detail.svelte';
	import PageLoading from '$lib/components/page-loading.svelte';
	import PageLoadError from '$lib/components/page-load-error.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

{#await Promise.all([data.season, data.files])}
	<PageLoading message="Loading season…" />
{:then [season, episodeFiles]}
	{#if season}
		<SeasonDetail {season} episodeFiles={episodeFiles ?? []} />
	{:else}
		<PageLoadError
			title="Season unavailable"
			message="This season could not be loaded. It may have been deleted."
		/>
	{/if}
{:catch}
	<PageLoadError title="Season unavailable" />
{/await}
