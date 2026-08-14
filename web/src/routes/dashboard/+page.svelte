<script lang="ts">
	import * as Table from '$lib/components/ui/table/index.js';
	import { Progress } from '$lib/components/ui/progress/index.js';
	import RecommendedMediaCarousel from '$lib/components/recommended-media-carousel.svelte';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';
	import {
		formatBytes,
		getDownloadStateString,
		getTorrentQualityString,
		getTorrentStatusString
	} from '$lib/utils';
	import { getContext, onDestroy, onMount } from 'svelte';
	import client from '$lib/api';
	import type { MetaDataProviderSearchResult } from '$lib/api/api.d.ts';
	import type { PageProps } from './$types';

	const OWN_TORRENTS_POLL_INTERVAL_MS = 7000;

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	setCrumbs([{ label: 'Dashboard' }]);

	let { data }: PageProps = $props();
	let recommendedShows: MetaDataProviderSearchResult[] = $state([]);
	let showsLoading = $state(true);
	let showsError = $state(false);

	let recommendedMovies: MetaDataProviderSearchResult[] = $state([]);
	let moviesLoading = $state(true);
	let moviesError = $state(false);

	let ownTorrents = $state(data.ownTorrents ?? []);
	let ownTorrentsPollHandle: ReturnType<typeof setInterval> | undefined;
	let ownTorrentsRefreshing = false;

	function refreshOwnTorrents() {
		if (document.hidden || ownTorrentsRefreshing) return;
		ownTorrentsRefreshing = true;
		client
			.GET('/api/v1/torrent/mine')
			.then((res) => {
				if (res.data) ownTorrents = res.data;
			})
			.catch(() => {
				// keep showing the last known state; the next tick will retry
			})
			.finally(() => {
				ownTorrentsRefreshing = false;
			});
	}

	onMount(() => {
		if (ownTorrents.length > 0) {
			ownTorrentsPollHandle = setInterval(refreshOwnTorrents, OWN_TORRENTS_POLL_INTERVAL_MS);
		}
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

	onDestroy(() => {
		clearInterval(ownTorrentsPollHandle);
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
							<Table.Head>Progress</Table.Head>
							<Table.Head>Size</Table.Head>
							<Table.Head>Quality</Table.Head>
						</Table.Row>
					</Table.Header>
					<Table.Body>
						{#each ownTorrents as torrent (torrent.id)}
							<Table.Row>
								<Table.Cell class="font-medium">{torrent.title}</Table.Cell>
								<Table.Cell>
									{torrent.download_progress
										? getDownloadStateString(torrent.download_progress.state)
										: getTorrentStatusString(torrent.status)}
								</Table.Cell>
								<Table.Cell>
									{#if torrent.download_progress}
										<div class="flex items-center gap-2">
											<Progress value={torrent.download_progress.progress} class="w-32" />
											<span class="text-sm text-muted-foreground"
												>{torrent.download_progress.progress}%</span
											>
										</div>
									{:else}
										<span class="text-muted-foreground">—</span>
									{/if}
								</Table.Cell>
								<Table.Cell>
									{formatBytes(torrent.download_progress?.total_bytes) ?? '—'}
								</Table.Cell>
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
