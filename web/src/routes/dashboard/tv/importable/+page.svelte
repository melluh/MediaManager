<script lang="ts">
	import ImportableMediaPage from '$lib/components/importable-media-page.svelte';
	import { resolve } from '$app/paths';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<ImportableMediaPage
	isShow={true}
	title="Importable TV Shows"
	parentCrumbLabel="Shows"
	parentCrumbHref={resolve('/dashboard/tv', {})}
	crumb="Importable"
	description="Import TV shows detected in your library directory into MediaManager"
	importable={data.importable}
	emptyMessage="No importable TV shows detected."
/>
