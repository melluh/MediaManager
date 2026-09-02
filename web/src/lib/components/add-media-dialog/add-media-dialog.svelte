<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import Plus from '@lucide/svelte/icons/plus';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Film from '@lucide/svelte/icons/film';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import type { MetaDataProviderSearchResult, Movie, Show } from '$lib/api/api';
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

	let loading = $state(false);
	let errorMessage = $state<string | null>(null);
	let backdropImageLoaded = $state(false);
	let posterImageLoaded = $state(false);
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
	}

	async function addMedia() {
		loading = true;
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
			loading = false;
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
		loading = false;
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
		<DetailsPage {detailsLoaded} {tagline} {overview} />
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
		{:else}
			<Button class="w-full font-semibold" disabled={loading} onclick={addMedia}>
				{#if loading}
					<LoaderCircle class="animate-spin" />
					<span class="animate-pulse">Adding...</span>
				{:else}
					<Plus />
					{`Add ${isShow ? 'Show' : 'Movie'}`}
				{/if}
			</Button>
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
