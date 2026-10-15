<script lang="ts">
	import DownloadsCarousel from '$lib/components/downloads/downloads-carousel.svelte';
	import RecommendedMediaCarousel from '$lib/components/recommended-media-carousel.svelte';
	import RatingPromptCard from '$lib/components/rating-prompt-card.svelte';
	import { onMount } from 'svelte';
	import { setCrumbs } from '$lib/context.svelte';
	import { poll } from '$lib/hooks/poll.svelte';
	import { recommendationReason } from '$lib/rating';
	import client from '$lib/api';
	import type {
		MetaDataProviderSearchResult,
		PersonalRecommendation,
		RatingPrompt,
		TorrentWithProgress
	} from '$lib/api/api.d.ts';

	setCrumbs([{ label: 'Dashboard' }]);

	let recommendedShows: MetaDataProviderSearchResult[] = $state([]);
	let showsLoading = $state(true);
	let showsError = $state(false);

	let recommendedMovies: MetaDataProviderSearchResult[] = $state([]);
	let moviesLoading = $state(true);
	let moviesError = $state(false);

	// Fetched here rather than in a `load` so the dashboard paints its layout right
	// away instead of waiting on the backend - see `routes/dashboard/+layout.ts`.
	// Only polled while there's something to show, so a user without downloads
	// doesn't keep hitting the backend.
	let ownTorrents: TorrentWithProgress[] = $state([]);
	async function refreshOwnTorrents() {
		const { data } = await client.GET('/api/v1/torrent/mine');
		if (data) ownTorrents = data;
	}
	let hasOwnTorrents = $derived(ownTorrents.length > 0);
	poll(refreshOwnTorrents, 7000, { enabled: () => hasOwnTorrents, immediate: false });

	// Recently watched movies the user hasn't rated yet. Empty (and the card
	// hidden) without a linked media server account, or if the request fails.
	let ratingPrompts: RatingPrompt[] = $state([]);

	// Based on what the user rated and watched. Empty (and the section hidden)
	// until they've rated or watched something, or if the request fails.
	let personalMovies: PersonalRecommendation[] = $state([]);
	let personalShows: PersonalRecommendation[] = $state([]);

	function reasonFor(recommendations: PersonalRecommendation[]) {
		const reasons = new Map(
			recommendations.map((r) => [
				r.media.external_id,
				recommendationReason(r.because_of, r.because_score)
			])
		);
		return (item: MetaDataProviderSearchResult) => reasons.get(item.external_id);
	}

	onMount(() => {
		client
			.GET('/api/v1/recommendations/movies')
			.then(({ data }) => {
				if (data) personalMovies = data;
			})
			.catch(() => {
				// nothing to recommend; the section stays hidden
			});

		client
			.GET('/api/v1/recommendations/shows')
			.then(({ data }) => {
				if (data) personalShows = data;
			})
			.catch(() => {
				// nothing to recommend; the section stays hidden
			});

		client
			.GET('/api/v1/ratings/movies/prompts')
			.then(({ data }) => {
				if (data) ratingPrompts = data;
			})
			.catch(() => {
				// nothing to ask about; the card stays hidden
			});

		refreshOwnTorrents().catch(() => {
			// nothing to show; the user simply sees no downloads section
		});

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
			<div class="mx-auto mb-8">
				<h3 class="my-4 text-2xl font-semibold lg:pointer-fine:ml-12">Your Downloads</h3>
				<DownloadsCarousel
					torrents={ownTorrents}
					onChange={() => refreshOwnTorrents().catch(() => {})}
				/>
			</div>
		{/if}

		<RatingPromptCard prompts={ratingPrompts} />

		{#if personalMovies.length > 0}
			<div class="mx-auto mb-8">
				<h3 class="my-4 text-2xl font-semibold lg:pointer-fine:ml-12">Movies for You</h3>
				<RecommendedMediaCarousel
					isLoading={false}
					isShow={false}
					media={personalMovies.map((r) => r.media)}
					caption={reasonFor(personalMovies)}
				/>
			</div>
		{/if}

		{#if personalShows.length > 0}
			<div class="mx-auto mb-8">
				<h3 class="my-4 text-2xl font-semibold lg:pointer-fine:ml-12">Shows for You</h3>
				<RecommendedMediaCarousel
					isLoading={false}
					isShow={true}
					media={personalShows.map((r) => r.media)}
					caption={reasonFor(personalShows)}
				/>
			</div>
		{/if}

		<div class="mx-auto">
			<h3 class="my-4 text-2xl font-semibold lg:pointer-fine:ml-12">Trending Shows</h3>
			<RecommendedMediaCarousel
				isLoading={showsLoading}
				isError={showsError}
				isShow={true}
				media={recommendedShows}
			/>

			<h3 class="my-4 mt-8 text-2xl font-semibold lg:pointer-fine:ml-12">Trending Movies</h3>
			<RecommendedMediaCarousel
				isLoading={moviesLoading}
				isError={moviesError}
				isShow={false}
				media={recommendedMovies}
			/>
		</div>
	</main>
</div>
