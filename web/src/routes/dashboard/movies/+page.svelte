<script lang="ts">
	import MediaLibraryPage from '$lib/components/media-library-page.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<MediaLibraryPage
	isShow={false}
	title="Movies"
	crumb="Movies"
	description="Browse and manage your movie collection in MediaManager"
	items={data.movies}
	importable={data.importable}
	emptyMessage="No movies added yet."
/>
