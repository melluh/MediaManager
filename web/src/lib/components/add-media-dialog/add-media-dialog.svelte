<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import Download from '@lucide/svelte/icons/download';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import Plus from '@lucide/svelte/icons/plus';
	import SearchX from '@lucide/svelte/icons/search-x';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Film from '@lucide/svelte/icons/film';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import type { IndexerQueryResult, MetaDataProviderSearchResult, Movie, Show } from '$lib/api/api';
	import client from '$lib/api';
	import { fetchMediaDetailsCached } from '$lib/api/media-details';
	import ExternalPosterImage from '$lib/components/external-poster-image.svelte';
	import {
		formatRuntime,
		getLanguageDisplayName,
		getMetadataProviderLabel,
		getMetadataProviderUrl
	} from '$lib/utils';
	import Skeleton from '$lib/components/ui/skeleton/skeleton.svelte';
	import { Spinner } from '$lib/components/ui/spinner';
	import DetailsPage from './details-page.svelte';
	import DownloadPage from './download-page.svelte';
	import {
		bucketTorrentQuality,
		getBestAvailableQuality,
		getBestTorrentPerQuality,
		getQualitySummaryLabel,
		getUpcomingReleaseLabel,
		isReleaseUpcoming,
		type AddMediaPageId,
		type MediaQuality,
		type QualityCounts
	} from './types';

	// Ordered pages of the dialog. To add a page (e.g. a "seasons" step for
	// shows), add its id here, render it alongside the others in the sliding
	// track below, and add a matching branch to the footer.
	const pages: AddMediaPageId[] = ['details', 'download'];

	let loadingAction: 'add' | 'download' | null = $state(null);
	let loading = $derived(loadingAction !== null);
	let errorMessage = $state<string | null>(null);
	let backdropImageLoaded = $state(false);
	let posterImageLoaded = $state(false);
	let currentPageIndex = $state(0);
	let selectedQuality = $state<MediaQuality | undefined>(undefined);
	let {
		result,
		isShow = true,
		open = false
	}: { result: MetaDataProviderSearchResult; isShow: boolean; open?: boolean } = $props();

	// Full metadata fetched in the background once the dialog is opened; supplements
	// the search-result data with fields the search endpoint doesn't provide (tagline)
	// and fresher runtime/genres/overview.
	let details = $state<Show | Movie | null>(null);
	let detailsFetched = false;
	let detailsLoaded = $state(false);

	// Torrent search kicks off as soon as the dialog opens (movies only, and
	// only if the movie isn't already in the library) so results are ready by
	// the time the user reaches the download page.
	let torrentSearchState = $state<'idle' | 'loading' | 'done' | 'error'>('idle');
	let torrents = $state<IndexerQueryResult[] | null>(null);
	let torrentsFetched = false;

	let qualityCounts = $derived.by(() => {
		const counts: QualityCounts = { '4k': 0, '1080p': 0, '720p': 0, lower: 0 };
		for (const torrent of torrents ?? []) {
			counts[bucketTorrentQuality(torrent.quality)]++;
		}
		return counts;
	});
	let totalTorrentsFound = $derived(torrents?.length ?? 0);
	let bestAvailableQuality = $derived(getBestAvailableQuality(qualityCounts));
	let noTorrentsFound = $derived(torrentSearchState === 'done' && totalTorrentsFound === 0);
	let selectedTorrents = $derived(getBestTorrentPerQuality(torrents ?? []));

	let isUnreleased = $derived(!isShow && isReleaseUpcoming(details?.release_date));
	let releaseLabel = $derived(
		details?.release_date ? getUpcomingReleaseLabel(details.release_date) : null
	);

	// Skip the quality/download page entirely when there's nothing to download
	// yet: the movie hasn't released, or the search came back empty.
	let skipDownloadFlow = $derived(isUnreleased || noTorrentsFound);

	let overview = $derived(details?.overview ?? result.overview);
	let runtime = $derived(details?.runtime ?? result.runtime);
	let genres = $derived(
		details?.genres && details.genres.length > 0 ? details.genres : result.genres
	);
	let tagline = $derived(details?.tagline);
	let language = $derived(getLanguageDisplayName(details?.original_language));
	let providerUrl = $derived(
		getMetadataProviderUrl(result.metadata_provider, result.external_id, isShow)
	);
	let providerLabel = $derived(getMetadataProviderLabel(result.metadata_provider));
	let imdbUrl = $derived(
		details?.imdb_id ? `https://www.imdb.com/title/${details.imdb_id}/` : null
	);

	$effect(() => {
		if (open) {
			currentPageIndex = 0;
			selectedQuality = undefined;
			if (!detailsFetched) {
				detailsFetched = true;
				fetchDetails();
			}
		}
	});

	async function fetchDetails() {
		const data = await fetchMediaDetailsCached(result, isShow);
		if (data) {
			details = data;
			detailsLoaded = true;
		}
		// Wait for the release date before searching torrents: there's nothing
		// to find for a movie that hasn't come out yet.
		if (!isShow && !result.added && !isReleaseUpcoming(data?.release_date) && !torrentsFetched) {
			torrentsFetched = true;
			searchTorrents();
		}
	}

	async function searchTorrents() {
		torrentSearchState = 'loading';
		const { data } = await client.GET('/api/v1/movies/external/{movie_id}/torrents', {
			params: {
				path: { movie_id: result.external_id },
				query: {
					metadata_provider: result.metadata_provider as 'tmdb' | 'tvdb',
					language: result.original_language ?? undefined
				}
			}
		});
		if (data) {
			torrents = data;
			torrentSearchState = 'done';
		} else {
			torrentSearchState = 'error';
		}
	}

	function goToDownloadPage() {
		currentPageIndex = pages.indexOf('download');
	}

	function goToDetailsPage() {
		currentPageIndex = pages.indexOf('details');
	}

	async function addMedia(action: 'add' | 'download' = 'add') {
		loadingAction = action;
		const query = {
			metadata_provider: result.metadata_provider as 'tmdb' | 'tvdb',
			language: result.original_language ?? undefined
		};
		const { data, error, response } = isShow
			? await client.POST('/api/v1/tv/shows', {
					params: { query: { show_id: result.external_id, ...query } }
				})
			: await client.POST('/api/v1/movies', {
					params: { query: { movie_id: result.external_id, ...query } }
				});

		// openapi-fetch returns `error: undefined` for a non-ok response with an
		// empty body (e.g. a 500 with no body), so `!response.ok` must be checked too.
		if (!response.ok || error) {
			errorMessage =
				`Failed to add ${isShow ? 'show' : 'movie'} to the library. ` +
				(error?.detail ? String(error.detail) : 'Please try again later.');
			loadingAction = null;
			return;
		}

		await goto(
			resolve(
				isShow ? '/dashboard/tv/[showId]' : '/dashboard/movies/[movieId]',
				isShow
					? { showId: data?.slug ?? data?.id ?? '' }
					: { movieId: data?.slug ?? data?.id ?? '' }
			),
			{ invalidateAll: true }
		);
		loadingAction = null;
	}

	// Backend torrent search/download by quality isn't wired up yet, so this
	// just adds the media for now, same as "Add without downloading".
	async function downloadMedia() {
		await addMedia('download');
	}
</script>

<Dialog.Content
	class="flex h-[90vh] w-[95vw] max-w-4xl flex-col gap-0 overflow-hidden border-0 p-0"
>
	{#if (result.backdrop_images?.length ?? 0) > 0}
		<div class="relative h-48 w-full shrink-0 bg-muted sm:h-64 md:h-72">
			<ExternalPosterImage
				className="h-full w-full object-cover object-center"
				posterImages={result.backdrop_images ?? []}
				alt={`${result.name}'s Backdrop Image`}
				sizes="95vw"
				loading="eager"
				bind:loaded={backdropImageLoaded}
			/>
			{#if !backdropImageLoaded}
				<div class="absolute inset-0 flex items-center justify-center">
					<Spinner class="size-8" />
				</div>
			{/if}
		</div>
	{/if}
	<div class="relative z-10 flex shrink-0 flex-row gap-4 p-6 text-left">
		{#if (result.poster_images?.length ?? 0) > 0}
			<div class="relative -mt-16 hidden h-44 w-32 shrink-0 sm:-mt-20 sm:h-56 sm:w-36 md:block">
				<ExternalPosterImage
					className="h-full w-full rounded-lg object-cover shadow-lg ring-1 ring-border"
					posterImages={result.poster_images ?? []}
					alt={`${result.name}'s Poster Image`}
					sizes="144px"
					bind:loaded={posterImageLoaded}
				/>
				{#if !posterImageLoaded}
					<div class="absolute inset-0 flex items-center justify-center rounded-lg bg-muted">
						<Spinner class="size-6" />
					</div>
				{/if}
			</div>
		{/if}

		<div class="flex min-w-0 flex-1 flex-col gap-2">
			<div class="flex flex-wrap items-start justify-between gap-2">
				<h2 class="text-xl font-bold sm:text-2xl">
					{result.name}
					{#if result.year != null}
						<span class="font-light">
							({result.year})
						</span>
					{/if}
				</h2>
				<div class="flex shrink-0 items-center gap-2">
					{#if !detailsLoaded}
						<Skeleton class="h-8 w-20" />
						<Skeleton class="h-8 w-20" />
					{:else}
						{#if details?.trailer_url}
							<Button
								variant="outline"
								size="sm"
								href={details?.trailer_url}
								target="_blank"
								rel="noopener noreferrer"
							>
								Trailer
								<Film />
							</Button>
						{/if}
						{#if imdbUrl}
							<Button
								variant="link"
								size="sm"
								href={imdbUrl}
								target="_blank"
								rel="noopener noreferrer"
							>
								IMDb
							</Button>
						{/if}
					{/if}
					{#if providerUrl}
						<Button
							variant="link"
							size="sm"
							href={providerUrl}
							target="_blank"
							rel="noopener noreferrer"
						>
							{providerLabel}
						</Button>
					{/if}
				</div>
			</div>

			{#if detailsLoaded}
				<span class="text-sm text-muted-foreground">
					{#if formatRuntime(runtime)}
						{formatRuntime(runtime)}
						&middot;
					{/if}
					{language}
				</span>
			{:else}
				<Skeleton class="h-5 w-24" />
			{/if}

			<div class="flex flex-wrap items-center gap-y-1 text-sm text-muted-foreground">
				{#if genres && genres.length > 0}
					<div class="flex flex-wrap gap-1">
						{#each genres as genre (genre)}
							<Badge variant="secondary">{genre}</Badge>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	</div>

	<div class="relative flex-1 overflow-hidden">
		<div
			class="flex h-full transition-transform duration-300 ease-in-out"
			style={`width: ${pages.length * 100}%; transform: translateX(-${
				(currentPageIndex * 100) / pages.length
			}%);`}
		>
			<div class="h-full shrink-0" style={`width: ${100 / pages.length}%`}>
				<DetailsPage {detailsLoaded} {tagline} {overview} />
			</div>
			<div class="h-full shrink-0" style={`width: ${100 / pages.length}%`}>
				<DownloadPage
					bind:selectedQuality
					{torrentSearchState}
					selectedTorrents={torrentSearchState === 'done' ? selectedTorrents : undefined}
				/>
			</div>
		</div>
	</div>

	<Dialog.Footer class="shrink-0 flex-col items-stretch gap-2 p-6 sm:flex-col">
		{#if result.added}
			<Button
				class="w-full font-semibold"
				variant="secondary"
				href={resolve(
					isShow ? '/dashboard/tv/[showId]' : '/dashboard/movies/[movieId]',
					isShow
						? { showId: result.slug ?? result.id ?? '' }
						: { movieId: result.slug ?? result.id ?? '' }
				)}
			>
				{isShow ? 'Show already exists' : 'Movie already exists'}
			</Button>
		{:else if currentPageIndex === 0}
			<div class="flex items-center gap-2">
				{#if isUnreleased && releaseLabel}
					<p class="flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
						<CalendarClock class="size-4" />
						{releaseLabel}
					</p>
				{:else if torrentSearchState === 'loading'}
					<p class="flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
						<Spinner class="size-4" />
						Searching for torrents...
					</p>
				{:else if torrentSearchState === 'done' && totalTorrentsFound > 0 && bestAvailableQuality}
					<p class="flex items-center gap-1.5 text-sm font-medium text-green-600">
						<CircleCheck class="size-4" />
						{totalTorrentsFound}
						{totalTorrentsFound === 1 ? 'torrent' : 'torrents'} available
						<span aria-hidden="true">&middot;</span>
						{getQualitySummaryLabel(bestAvailableQuality)}
					</p>
				{:else if noTorrentsFound}
					<p class="flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
						<SearchX class="size-4" />
						No torrents found
					</p>
				{/if}
				<Button
					class="ml-auto font-semibold"
					disabled={loading}
					onclick={skipDownloadFlow ? () => addMedia('add') : goToDownloadPage}
				>
					{#if skipDownloadFlow}
						{#if loadingAction === 'add'}
							<LoaderCircle class="animate-spin" />
							<span class="animate-pulse">Adding...</span>
						{:else}
							<Plus />
							{`Add ${isShow ? 'Show' : 'Movie'}`}
						{/if}
					{:else}
						{`Add ${isShow ? 'Show' : 'Movie'}`}
						<ArrowRight />
					{/if}
				</Button>
			</div>
		{:else}
			<div class="flex items-center justify-between gap-2">
				<Button variant="ghost" class="font-semibold" disabled={loading} onclick={goToDetailsPage}>
					<ArrowLeft />
					Back
				</Button>
				<div class="flex items-center gap-2">
					<Button
						variant="secondary"
						class="font-semibold"
						disabled={loading}
						onclick={() => addMedia('add')}
					>
						{#if loadingAction === 'add'}
							<LoaderCircle class="animate-spin" />
							<span class="animate-pulse">Adding...</span>
						{:else}
							<Plus />
							Add without downloading
						{/if}
					</Button>
					<Button
						class="font-semibold"
						disabled={loading || !selectedQuality}
						onclick={downloadMedia}
					>
						{#if loadingAction === 'download'}
							<LoaderCircle class="animate-spin" />
							<span class="animate-pulse">Downloading...</span>
						{:else}
							<Download />
							Download
						{/if}
					</Button>
				</div>
			</div>
		{/if}
	</Dialog.Footer>
</Dialog.Content>

<AlertDialog.Root open={errorMessage !== null} onOpenChange={() => (errorMessage = null)}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title class="flex items-center gap-2">
				<TriangleAlert class="size-5 text-destructive" />
				Something went wrong
			</AlertDialog.Title>
			<AlertDialog.Description>{errorMessage}</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Action onclick={() => (errorMessage = null)}>OK</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
