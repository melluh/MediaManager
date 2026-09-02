<script lang="ts">
	import PageLoading from '$lib/components/page-loading.svelte';
	import PageLoadError from '$lib/components/page-load-error.svelte';
	import { setContext } from 'svelte';
	import type { PublicShow, RichShowTorrent } from '$lib/api/api';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();

	// The show is resolved here rather than in `load` so this route paints a loading
	// indicator instead of a blank page. Children read it back off the context.
	let show = $state<PublicShow | undefined>(undefined);
	let torrents = $state<RichShowTorrent | undefined>(undefined);
	let status = $state<'loading' | 'ready' | 'error'>('loading');
	let errorMessage = $state('');

	setContext('show', () => show);
	setContext('showTorrents', () => torrents);

	$effect(() => {
		const pending = data.show;
		let cancelled = false;
		status = 'loading';

		pending
			.then((details) => {
				if (cancelled) return;
				show = details.show;
				torrents = details.torrents;
				status = 'ready';
			})
			.catch((e: Error) => {
				if (cancelled) return;
				errorMessage = e.message;
				status = 'error';
			});

		return () => {
			cancelled = true;
		};
	});
</script>

{#if status === 'error'}
	<PageLoadError title="Show unavailable" message={errorMessage} />
{:else if status === 'loading' || !show}
	<PageLoading message="Loading show…" />
{:else}
	{@render children()}
{/if}
