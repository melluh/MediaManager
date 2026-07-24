<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { LoaderCircle } from 'lucide-svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import type { MetaDataProviderSearchResult, Movie, Show } from '$lib/api/api';
	import client from '$lib/api';
	import ExternalPosterImage from '$lib/components/external-poster-image.svelte';
	import { formatRuntime, getLanguageDisplayName } from '$lib/utils';
	import Skeleton from './ui/skeleton/skeleton.svelte';

	let loading = $state(false);
	let errorMessage = $state<string | null>(null);
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

	$effect(() => {
		if (open && !detailsFetched) {
			detailsFetched = true;
			fetchDetails();
		}
	});

	async function fetchDetails() {
		const params = {
			query: {
				metadata_provider: result.metadata_provider as 'tmdb' | 'tvdb',
				language: result.original_language ?? undefined
			}
		};
		if (isShow) {
			const { data } = await client.GET('/api/v1/tv/external/{show_id}', {
				params: { ...params, path: { show_id: result.external_id } }
			});
			if (data) {
				details = data;
				detailsLoaded = true;
			}
		} else {
			const { data } = await client.GET('/api/v1/movies/external/{movie_id}', {
				params: { ...params, path: { movie_id: result.external_id } }
			});
			if (data) {
				details = data;
				detailsLoaded = true;
			}
		}
	}

	async function addMedia() {
		loading = true;
		let data;
		if (isShow) {
			const response = await client.POST('/api/v1/tv/shows', {
				params: {
					query: {
						show_id: result.external_id,
						metadata_provider: result.metadata_provider as 'tmdb' | 'tvdb',
						language: result.original_language ?? undefined
					}
				}
			});
			data = response.data;
		} else {
			const response = await client.POST('/api/v1/movies', {
				params: {
					query: {
						movie_id: result.external_id,
						metadata_provider: result.metadata_provider as 'tmdb' | 'tvdb',
						language: result.original_language ?? undefined
					}
				}
			});
			data = response.data;
		}

		if (isShow) {
			await goto(resolve('/dashboard/tv/[showId]', { showId: data?.id ?? '' }), {
				invalidateAll: true
			});
		} else {
			await goto(resolve('/dashboard/movies/[movieId]', { movieId: data?.id ?? '' }), {
				invalidateAll: true
			});
		}
		loading = false;
	}
</script>

<Dialog.Content class="flex h-[90vh] w-[95vw] max-w-4xl flex-col gap-0 overflow-hidden border-0 p-0">
	{#if (result.backdrop_images?.length ?? 0) > 0}
		<div class="relative h-48 w-full shrink-0 bg-muted sm:h-64 md:h-72">
			<ExternalPosterImage
				className="h-full w-full object-cover object-center"
				posterImages={result.backdrop_images ?? []}
				alt={`${result.name}'s Backdrop Image`}
				sizes="95vw"
				loading="eager"
			/>
		</div>
	{/if}
	<div class="relative z-10 shrink-0 flex flex-row gap-4 p-6 text-left">
		{#if (result.poster_images?.length ?? 0) > 0}
			<ExternalPosterImage
				className="h-44 w-32 shrink-0 rounded-lg object-cover shadow-lg ring-1 ring-border sm:h-56 sm:w-36 -mt-16 sm:-mt-20"
				posterImages={result.poster_images ?? []}
				alt={`${result.name}'s Poster Image`}
				sizes="144px"
			/>
		{/if}

		<div class="flex flex-col gap-2">
			<h2 class="text-xl font-bold sm:text-2xl">
				{result.name}
				{#if result.year != null}
					<span class="font-light">
						({result.year})
					</span>
				{/if}
			</h2>

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

	<div class="flex-1 overflow-y-auto">
		<div class="flex flex-col gap-3 px-6 pb-6">
			<!-- <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">

				{#if result.vote_average != null}
					<span class="flex items-center text-sm font-medium text-yellow-600">
						<svg class="mr-1 h-4 w-4 text-yellow-400" fill="currentColor" viewBox="0 0 20 20"
							><path
								d="M10 15l-5.878 3.09 1.122-6.545L.488 6.91l6.561-.955L10 0l2.951 5.955 6.561.955-4.756 4.635 1.122 6.545z"
							/></svg
						>
						Rating: {Math.round(result.vote_average)}/10
					</span>
				{/if}
			</div> -->

			{#if detailsLoaded}
				{#if tagline}
					<p class="text-lg font-medium italic text-muted-foreground">{tagline}</p>
				{/if}
			{:else}
				<Skeleton class="h-6 w-64" />
			{/if}

			<p class="text-base text-muted-foreground">
				{overview !== '' && overview != null ? overview : 'No overview available'}
			</p>
		</div>
	</div>
	<Dialog.Footer class="shrink-0 flex-col items-stretch gap-2 p-6 sm:flex-col">
		{#if result.added}
			<Button
				class="w-full font-semibold"
				variant="secondary"
				href={resolve(
					isShow ? '/dashboard/tv/[showId]' : '/dashboard/movies/[movieId]',
					isShow ? { showId: result.id ?? '' } : { movieId: result.id ?? '' }
				)}
			>
				{isShow ? 'Show already exists' : 'Movie already exists'}
			</Button>
		{:else}
			<Button class="w-full font-semibold" disabled={loading} onclick={() => addMedia()}>
				{#if loading}
					<LoaderCircle class="mr-2 h-4 w-4 animate-spin" />
					<span class="animate-pulse">Loading...</span>
				{:else}
					{`Add ${isShow ? 'Show' : 'Movie'}`}
				{/if}
			</Button>
		{/if}
		{#if errorMessage}
			<p class="w-full rounded bg-red-50 px-2 py-1 text-xs text-red-500">{errorMessage}</p>
		{/if}
	</Dialog.Footer>
</Dialog.Content>
