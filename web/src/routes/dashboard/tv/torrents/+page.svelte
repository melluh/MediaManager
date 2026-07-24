<script lang="ts">
	import { page } from '$app/state';
	import { getFullyQualifiedMediaName } from '$lib/utils';
	import * as Accordion from '$lib/components/ui/accordion/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import TorrentTable from '$lib/components/torrents/torrent-table.svelte';
	import { resolve } from '$app/paths';
	import { getContext } from 'svelte';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	setCrumbs([{ label: 'Shows', href: resolve('/dashboard/tv', {}) }, { label: 'TV Torrents' }]);
</script>

<svelte:head>
	<title>TV Show Torrents - MediaManager</title>
	<meta content="View and manage TV show torrent downloads in MediaManager" name="description" />
</svelte:head>

<div class="mx-auto flex w-full flex-1 flex-col gap-4 p-4 md:max-w-[80em]">
	<h1 class="scroll-m-20 text-center text-4xl font-extrabold tracking-tight lg:text-5xl">
		TV Torrents
	</h1>
	<Accordion.Root type="single" class="w-full">
		{#each page.data.torrents as show (show.show_id)}
			<div class="p-6">
				<Card.Root>
					<Card.Header>
						<Card.Title>
							{getFullyQualifiedMediaName(show)}
						</Card.Title>
					</Card.Header>
					<Card.Content>
						<TorrentTable isShow={true} torrents={show.torrents} showId={show.show_id} />
					</Card.Content>
				</Card.Root>
			</div>
		{:else}
			<div class="col-span-full text-center text-muted-foreground">No Torrents added yet.</div>
		{/each}
	</Accordion.Root>
</div>
