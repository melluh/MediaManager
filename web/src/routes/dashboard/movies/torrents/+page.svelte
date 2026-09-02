<script lang="ts">
	import { getFullyQualifiedMediaName } from '$lib/utils';
	import * as Accordion from '$lib/components/ui/accordion/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import TorrentTable from '$lib/components/torrents/torrent-table.svelte';
	import { resolve } from '$app/paths';
	import { getContext } from 'svelte';
	import PageLoading from '$lib/components/page-loading.svelte';
	import type { PageProps } from './$types';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';

	let { data }: PageProps = $props();

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	setCrumbs([
		{ label: 'Movies', href: resolve('/dashboard/movies', {}) },
		{ label: 'Movie Torrents' }
	]);
</script>

<svelte:head>
	<title>Movie Torrents - MediaManager</title>
	<meta content="View and manage movie torrent downloads in MediaManager" name="description" />
</svelte:head>

<main class="mx-auto flex w-full flex-1 flex-col gap-4 p-4 md:max-w-[80em]">
	<h1 class="scroll-m-20 text-center text-4xl font-extrabold tracking-tight lg:text-5xl">
		Movie Torrents
	</h1>
	<Accordion.Root class="w-full" type="single">
		{#await data.torrents}
			<PageLoading message="Loading torrents…" />
		{:then torrents}
			{#each torrents ?? [] as movie (movie.movie_id)}
				<div class="p-6">
					<Card.Root>
						<Card.Header>
							<Card.Title>
								{getFullyQualifiedMediaName(movie)}
							</Card.Title>
						</Card.Header>
						<Card.Content>
							<TorrentTable isShow={false} torrents={movie.torrents} movieSlug={movie.slug} />
						</Card.Content>
					</Card.Root>
				</div>
			{:else}
				<div class="col-span-full text-center text-muted-foreground">No Torrents added yet.</div>
			{/each}
		{/await}
	</Accordion.Root>
</main>
