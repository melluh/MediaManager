<script lang="ts">
	import ImportableMediaPage from '$lib/components/importable-media-page.svelte';
	import { resolve } from '$app/paths';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<ImportableMediaPage
	isShow={false}
	title="Importable Movies"
	parentCrumbLabel="Movies"
	parentCrumbHref={resolve('/dashboard/movies', {})}
	crumb="Importable"
	description="Import movies detected in your library directory into MediaManager"
	importable={data.importable}
	emptyMessage="No importable movies detected."
/>
