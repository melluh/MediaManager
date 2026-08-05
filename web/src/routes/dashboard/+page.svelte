<script lang="ts">
	import * as Table from '$lib/components/ui/table/index.js';
	import StatCard from '$lib/components/stats/stat-cards.svelte';
	import RecommendedMediaCarousel from '$lib/components/recommended-media-carousel.svelte';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';
	import { getTorrentQualityString, getTorrentStatusString } from '$lib/utils';
	import { getContext, onMount } from 'svelte';
	import client from '$lib/api';
	import type {
		MetaDataProviderSearchResult,
		MediaImportSuggestion,
		UserRead
	} from '$lib/api/api.d.ts';
	import type { PageProps } from './$types';

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	setCrumbs([{ label: 'Dashboard' }]);

	let { data }: PageProps = $props();
	let user: () => UserRead = getContext('user');
	let recommendedShows: MetaDataProviderSearchResult[] = $state([]);
	let showsLoading = $state(true);

	let recommendedMovies: MetaDataProviderSearchResult[] = $state([]);
	let moviesLoading = $state(true);

	let importableShows: MediaImportSuggestion[] = $state([]);
	let importableMovies: MediaImportSuggestion[] = $state([]);

	let ownTorrents = $derived(data.ownTorrents ?? []);

	onMount(async () => {
		client.GET('/api/v1/tv/recommended').then((res) => {
			recommendedShows = res.data as MetaDataProviderSearchResult[];
			showsLoading = false;
		});
		client.GET('/api/v1/movies/recommended').then((res) => {
			recommendedMovies = res.data as MetaDataProviderSearchResult[];
			moviesLoading = false;
		});
		if (user()?.is_superuser) {
			client.GET('/api/v1/movies/importable').then(({ data, error }) => {
				if (!error) {
					importableMovies = data;
				}
			});
			client.GET('/api/v1/tv/importable').then(({ data, error }) => {
				if (!error) {
					importableShows = data;
				}
			});
		}
	});
</script>

<svelte:head>
	<title>Dashboard - MediaManager</title>
	<meta
		content="MediaManager Dashboard - View your recommended movies and TV shows"
		name="description"
	/>
</svelte:head>

<div class="flex flex-1 flex-col gap-4 p-4 pt-0">
	<main class="min-h-screen flex-1 items-center justify-center rounded-xl p-4 md:min-h-min">
		<div class="mx-auto ml-12">
			<StatCard
				showCount={data.tvShows?.length ?? 0}
				moviesCount={data.movies?.length ?? 0}
				{importableShows}
				{importableMovies}
			/>
		</div>

		{#if ownTorrents.length > 0}
			<div class="mx-auto my-8 ml-12">
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
			<h3 class="my-4 ml-12 text-2xl font-semibold">Trending Shows</h3>
			<RecommendedMediaCarousel isLoading={showsLoading} isShow={true} media={recommendedShows} />

			<h3 class="my-4 mt-8 ml-12 text-2xl font-semibold">Trending Movies</h3>
			<RecommendedMediaCarousel
				isLoading={moviesLoading}
				isShow={false}
				media={recommendedMovies}
			/>
		</div>
	</main>
</div>
