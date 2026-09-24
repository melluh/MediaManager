<script lang="ts">
	import PageLoading from '$lib/components/page-loading.svelte';
	import PageLoadError from '$lib/components/page-load-error.svelte';
	import SeededMediaDetail from '$lib/components/seeded-media-detail.svelte';
	import { resolve } from '$app/paths';
	import { Resolved } from '$lib/hooks/resolved.svelte';
	import { setShowContext } from '$lib/context.svelte';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();

	// The show is resolved here rather than in `load` so this route paints a loading
	// indicator instead of a blank page. Children read it back off the context, and
	// only render once it has loaded.
	const details = new Resolved(() => data.show, { keepPrevious: false });

	setShowContext({
		show: () => details.value!.show,
		torrents: () => details.value!.torrents
	});
</script>

{#if details.status === 'error'}
	<PageLoadError
		title="Show unavailable"
		message={details.error instanceof Error ? details.error.message : String(details.error)}
	/>
{:else if details.status === 'loading' && data.seed}
	<SeededMediaDetail
		media={data.seed}
		isShow={true}
		crumbs={[{ label: 'Shows', href: resolve('/dashboard/tv', {}) }, { label: data.seed.name }]}
		message="Loading show…"
	/>
{:else if details.status === 'loading'}
	<PageLoading message="Loading show…" />
{:else}
	{@render children()}
{/if}
