<script lang="ts">
	import type { Snippet } from 'svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import Play from '@lucide/svelte/icons/play';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import type { PublicMovie, PublicShow } from '$lib/api/api';
	import client from '$lib/api';

	let {
		media,
		isShow,
		enabled,
		available = $bindable(false),
		fallback
	}: {
		media: PublicMovie | PublicShow;
		isShow: boolean;
		// Only look up a watch URL once something has actually been downloaded.
		enabled: boolean;
		// Whether a watch URL was found, so the parent can adjust its other actions.
		available?: boolean;
		// Rendered in place of the button when there's nothing to watch.
		fallback?: Snippet;
	} = $props();

	// Fetched separately from the media's own details so a slow/unconfigured
	// media server never blocks the detail page from loading.
	let watchUrl: string | null = $state(null);
	let watchMediaServerName: string | null = $state(null);
	let watchUrlLoading = $state(false);
	$effect(() => {
		watchUrl = null;
		watchMediaServerName = null;
		available = false;
		if (!enabled) return;
		watchUrlLoading = true;
		const request = isShow
			? client.GET('/api/v1/tv/shows/{show_id}/watch-url', {
					params: { path: { show_id: media.id! } }
				})
			: client.GET('/api/v1/movies/{movie_id}/watch-url', {
					params: { path: { movie_id: media.id! } }
				});
		request
			.then(({ data }) => {
				watchUrl = data?.url ?? null;
				watchMediaServerName = data?.media_server_name ?? null;
				available = watchUrl != null;
			})
			.finally(() => {
				watchUrlLoading = false;
			});
	});
</script>

{#if enabled && watchUrlLoading}
	<Button disabled class="bg-green-600 text-white hover:bg-green-700">
		<LoaderCircle class="animate-spin" />
		Watch
	</Button>
{:else if watchUrl}
	<Button
		href={watchUrl}
		target="_blank"
		rel="noopener noreferrer"
		class="bg-green-600 text-white hover:bg-green-700"
	>
		<Play />
		Watch on {watchMediaServerName}
	</Button>
{:else}
	{@render fallback?.()}
{/if}
