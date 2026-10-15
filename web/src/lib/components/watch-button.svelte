<script lang="ts">
	import type { Snippet } from 'svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import Play from '@lucide/svelte/icons/play';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import type { PublicMovie, PublicShow } from '$lib/api/api';
	import client from '$lib/api';
	import { meta } from '$lib/hooks/meta.svelte.js';

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
	let watchUrlLoading = $state(false);
	// Keyed on the id rather than `media` itself, so a refreshed copy of the
	// same media doesn't refetch (and flash) the watch URL.
	let mediaId = $derived(media.id!);
	$effect(() => {
		watchUrl = null;
		available = false;
		if (!enabled) return;
		watchUrlLoading = true;
		const request = isShow
			? client.GET('/api/v1/tv/shows/{show_id}/watch-url', {
					params: { path: { show_id: mediaId } }
				})
			: client.GET('/api/v1/movies/{movie_id}/watch-url', {
					params: { path: { movie_id: mediaId } }
				});
		// The button's label (the media server's name) comes from the
		// session-cached instance metadata, normally loaded long before this.
		Promise.all([request, meta.load()])
			.then(([{ data }, instanceMeta]) => {
				watchUrl = instanceMeta?.media_server ? (data?.url ?? null) : null;
				available = watchUrl != null;
			})
			.finally(() => {
				watchUrlLoading = false;
			});
	});
</script>

{#if enabled && watchUrlLoading}
	<Button disabled variant="brand">
		<LoaderCircle class="animate-spin" />
		{#if meta.current?.media_server}
			Watch on {meta.current.media_server.display_name}
		{:else}
			Watch
		{/if}
	</Button>
{:else if watchUrl && meta.current?.media_server}
	<Button href={watchUrl} target="_blank" rel="noopener noreferrer" variant="brand">
		<Play />
		Watch on {meta.current.media_server.display_name}
	</Button>
{:else}
	{@render fallback?.()}
{/if}
