<script lang="ts">
	import * as Table from '$lib/components/ui/table/index.js';
	import RecommendedMediaCarousel from '$lib/components/recommended-media-carousel.svelte';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';
	import { getTorrentQualityString, getTorrentStatusString } from '$lib/utils';
	import { getContext, onMount } from 'svelte';
	import client from '$lib/api';
	import type { MetaDataProviderSearchResult } from '$lib/api/api.d.ts';
	import type { PageProps } from './$types';

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	setCrumbs([{ label: 'Dashboard' }]);

	let { data }: PageProps = $props();
	let recommendedShows: MetaDataProviderSearchResult[] = $state([]);
	let showsLoading = $state(true);
	let showsError = $state(false);

	let recommendedMovies: MetaDataProviderSearchResult[] = $state([]);
	let moviesLoading = $state(true);
	let moviesError = $state(false);

	let ownTorrents = $derived(data.ownTorrents ?? []);

	onMount(() => {
		client
			.GET('/api/v1/tv/recommended')
			.then((res) => {
				if (res.error || !res.data) {
					showsError = true;
					return;
				}
				recommendedShows = res.data;
			})
			.catch(() => {
				showsError = true;
			})
			.finally(() => {
				showsLoading = false;
			});

		client
			.GET('/api/v1/movies/recommended')
			.then((res) => {
				if (res.error || !res.data) {
					moviesError = true;
					return;
				}
				recommendedMovies = res.data;
			})
			.catch(() => {
				moviesError = true;
			})
			.finally(() => {
				moviesLoading = false;
			});
	});
</script>

<svelte:head>
	<title>Dashboard - MediaManager</title>
	<meta
		content="MediaManager Dashboard - View your recommended movies and TV shows"
		name="description"
	/>
</svelte:head>

<div class="flex flex-1 flex-col gap-4 pt-0 md:p-4 md:pt-0">
	<main class="min-h-screen flex-1 items-center justify-center rounded-xl p-4 md:min-h-min">
		{#if ownTorrents.length > 0}
			<div class="mx-auto my-8 md:ml-12">
				<h3 class="my-4 text-2xl font-semibold">Your Downloads</h3>

				<Table.Root>
					<Table.Header>
						<Table.Row>
							<Table.Head>Name</Table.Head>
							<Table.Head>Download Status</Table.Head>
							<Table.Head>Quality</Table.Head>
						</Table.Row>
					</Table.Header>
					<Table.Body>
						{#each ownTorrents as torrent (torrent.id)}
							<Table.Row>
								<Table.Cell class="font-medium">{torrent.title}</Table.Cell>
								<Table.Cell>{getTorrentStatusString(torrent.status)}</Table.Cell>
								<Table.Cell>{getTorrentQualityString(torrent.quality)}</Table.Cell>
							</Table.Row>
						{/each}
					</Table.Body>
				</Table.Root>
			</div>
		{/if}

		<div class="mx-auto">
			<h3 class="my-4 text-2xl font-semibold md:ml-12">Trending Shows</h3>
			<RecommendedMediaCarousel
				isLoading={showsLoading}
				isError={showsError}
				isShow={true}
				media={recommendedShows}
			/>

			<h3 class="my-4 mt-8 text-2xl font-semibold md:ml-12">Trending Movies</h3>
			<RecommendedMediaCarousel
				isLoading={moviesLoading}
				isError={moviesError}
				isShow={false}
				media={recommendedMovies}
			/>
		</div>
	</main>
</div>
