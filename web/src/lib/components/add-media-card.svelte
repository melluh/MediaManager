<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { ChevronRight, ImageOff, LoaderCircle } from 'lucide-svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import type { MetaDataProviderSearchResult } from '$lib/api/api';
	import client from '$lib/api';
	import ExternalPosterImage from '$lib/components/external-poster-image.svelte';
	import { formatRuntime } from '$lib/utils';

	let loading = $state(false);
	let errorMessage = $state<string | null>(null);
	let detailsOpen = $state(false);
	let { result, isShow = true }: { result: MetaDataProviderSearchResult; isShow: boolean } =
		$props();

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

<Card.Root class="group col-span-full overflow-hidden sm:col-span-1">
	<Dialog.Root bind:open={detailsOpen}>
		<Dialog.Trigger
			class="relative block aspect-2/3 w-full cursor-pointer overflow-hidden rounded-xl text-left"
		>
			{#if (result.poster_images?.length ?? 0) > 0}
				<ExternalPosterImage
					className="h-full w-full object-cover"
					posterImages={result.poster_images ?? []}
					alt={`${result.name}'s Poster Image`}
				/>
			{:else}
				<div class="flex h-full w-full items-center justify-center bg-muted">
					<ImageOff class="h-12 w-12 text-gray-400" />
				</div>
			{/if}
			<div
				class="absolute inset-0 flex flex-col justify-end gap-1 bg-gradient-to-t from-black/90 via-black/40 to-transparent p-3 text-white opacity-0 transition-opacity duration-200 group-focus-within:opacity-100 group-hover:opacity-100"
			>
				<div class="flex items-start justify-between gap-2">
					<p class="leading-tight font-semibold">
						{result.name}
						{#if result.year != null}
							<span class="font-normal text-white/70">({result.year})</span>
						{/if}
					</p>
					<ChevronRight class="h-5 w-5 shrink-0 text-white/80" />
				</div>
				<div class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-white/80">
					{#if formatRuntime(result.runtime)}
						<span>{formatRuntime(result.runtime)}</span>
					{/if}
					{#if result.genres && result.genres.length > 0}
						<span>{result.genres.slice(0, 3).join(', ')}</span>
					{/if}
				</div>
			</div>
		</Dialog.Trigger>
		<Dialog.Content class="max-w-md">
			<Dialog.Header>
				<Dialog.Title>
					{result.name}
					{#if result.year != null}
						({result.year})
					{/if}
				</Dialog.Title>
			</Dialog.Header>
			<div class="flex flex-col gap-3">
				<div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
					{#if formatRuntime(result.runtime)}
						<span>{formatRuntime(result.runtime)}</span>
					{/if}
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
				</div>
				{#if result.genres && result.genres.length > 0}
					<div class="flex flex-wrap gap-1">
						{#each result.genres as genre (genre)}
							<Badge variant="secondary">{genre}</Badge>
						{/each}
					</div>
				{/if}
				<p class="text-sm text-muted-foreground">
					{result.overview !== '' && result.overview != null
						? result.overview
						: 'No overview available'}
				</p>
			</div>
			<Dialog.Footer class="flex-col items-stretch gap-2 sm:flex-col">
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
	</Dialog.Root>
</Card.Root>
