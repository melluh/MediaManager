<script lang="ts">
	import MediaLibraryPage from '$lib/components/media-library-page.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<MediaLibraryPage
	isShow={true}
	title="TV Shows"
	crumb="Shows"
	description="Browse and manage your TV show collection in MediaManager"
	items={data.tvShows}
	importable={data.importable}
	emptyMessage="No TV shows added yet."
/>
