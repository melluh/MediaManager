<script lang="ts">
	import { Separator } from '$lib/components/ui/separator/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import * as Breadcrumb from '$lib/components/ui/breadcrumb/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import StatCard from '$lib/components/stats/stat-cards.svelte';
	import RecommendedMediaCarousel from '$lib/components/recommended-media-carousel.svelte';
	import MediaSearchBox from '$lib/components/media-search-box.svelte';
	import { getTorrentQualityString, getTorrentStatusString } from '$lib/utils';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import client from '$lib/api';
	import type { MetaDataProviderSearchResult } from '$lib/api/api.d.ts';
	import type { PageProps } from './$types';
	let { data }: PageProps = $props();
	let recommendedShows: MetaDataProviderSearchResult[] = $state([]);
	let showsLoading = $state(true);

	let recommendedMovies: MetaDataProviderSearchResult[] = $state([]);
	let moviesLoading = $state(true);

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
	});
</script>

<svelte:head>
	<title>Dashboard - MediaManager</title>
	<meta
		content="MediaManager Dashboard - View your recommended movies and TV shows"
		name="description"
	/>
</svelte:head>

<header class="flex h-16 shrink-0 items-center gap-2">
	<div class="flex items-center gap-2 px-4">
		<Sidebar.Trigger class="-ml-1" />
		<Separator class="mr-2 h-4" orientation="vertical" />
		<Breadcrumb.Root>
			<Breadcrumb.List>
				<Breadcrumb.Item class="hidden md:block">
					<Breadcrumb.Link href={resolve('/dashboard', {})}>MediaManager</Breadcrumb.Link>
				</Breadcrumb.Item>
				<Breadcrumb.Separator class="hidden md:block" />
				<Breadcrumb.Item>
					<Breadcrumb.Page>Home</Breadcrumb.Page>
				</Breadcrumb.Item>
			</Breadcrumb.List>
		</Breadcrumb.Root>
	</div>
	<MediaSearchBox class="mr-4 ml-auto w-full max-w-md" />
</header>

<div class="flex flex-1 flex-col gap-4 p-4 pt-0">
	<h1 class="scroll-m-20 text-center text-4xl font-extrabold tracking-tight lg:text-5xl">
		Dashboard
	</h1>

	<main class="min-h-screen flex-1 items-center justify-center rounded-xl p-4 md:min-h-min">
		<div class="mx-auto">
			<div class="my-8 block text-2xl">Welcome to MediaManager!</div>

			<StatCard showCount={data.tvShows?.length ?? 0} moviesCount={data.movies?.length ?? 0} />
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
			<h3 class="my-4 text-2xl font-semibold ml-12">Trending Shows</h3>
			<RecommendedMediaCarousel
				isLoading={showsLoading}
				isShow={true}
				media={recommendedShows}
			/>

			<h3 class="my-4 text-2xl font-semibold ml-12 mt-8">Trending Movies</h3>
			<RecommendedMediaCarousel
				isLoading={moviesLoading}
				isShow={false}
				media={recommendedMovies}
			/>
		</div>
	</main>
</div>
