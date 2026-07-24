<script lang="ts">
	import * as Card from '$lib/components/ui/card/index.js';
	import { getFullyQualifiedMediaName } from '$lib/utils';
	import MediaPicture from '$lib/components/media-picture.svelte';
	import { resolve } from '$app/paths';
	import type { MediaImportSuggestion } from '$lib/api/api';
	import ImportCandidatesDialog from '$lib/components/import-media/import-candidates-dialog.svelte';
	import DetectedMediaCard from '$lib/components/import-media/detected-media-card.svelte';
	import { getContext } from 'svelte';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';
	import type { PageProps } from './$types';
	import LoadingBar from '$lib/components/loading-bar.svelte';

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	setCrumbs([{ label: 'Movies' }]);

	let { data }: PageProps = $props();
	let importableMovies: () => MediaImportSuggestion[] = getContext('importableMovies');
</script>

<svelte:head>
	<title>Movies - MediaManager</title>
	<meta content="Browse and manage your movie collection in MediaManager" name="description" />
</svelte:head>

<main class="flex w-full flex-1 flex-col gap-4 p-4 pt-0">
	<h1 class="scroll-m-20 text-center text-4xl font-extrabold tracking-tight lg:text-5xl">Movies</h1>
	{#if importableMovies().length > 0}
		<div
			class="grid w-full auto-rows-min gap-4 sm:grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-4"
		>
			{#each importableMovies() as importable (importable.directory)}
				<DetectedMediaCard isTv={false} directory={importable.directory}>
					<ImportCandidatesDialog
						isTv={false}
						name={importable.directory}
						candidates={importable.candidates}
					>
						Import movie
					</ImportCandidatesDialog>
				</DetectedMediaCard>
			{/each}
		</div>
	{/if}
	{#await data.movies}
		<LoadingBar />
	{:then movies}
		<div
			class="grid w-full auto-rows-min gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5"
		>
			{#each movies as movie (movie.id)}
				<a href={resolve('/dashboard/movies/[movieId]', { movieId: movie.id! })}>
					<Card.Root class="col-span-full max-w-[90vw] ">
						<Card.Header>
							<Card.Title class="h-6 truncate">{getFullyQualifiedMediaName(movie)}</Card.Title>
							<Card.Description class="truncate">{movie.overview}</Card.Description>
						</Card.Header>
						<Card.Content>
							<MediaPicture media={movie} />
						</Card.Content>
					</Card.Root>
				</a>
			{:else}
				<div class="col-span-full text-center text-muted-foreground">No movies added yet.</div>
			{/each}
		</div>
	{/await}
</main>
