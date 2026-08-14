<script lang="ts">
	import { getContext, type Snippet } from 'svelte';
	import MediaImage from '$lib/components/media-image.svelte';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import Film from '@lucide/svelte/icons/film';
	import {
		cn,
		getFullyQualifiedMediaName,
		formatRuntime,
		formatReleaseDate,
		formatLastUpdated,
		getMetadataProviderLabel,
		getMetadataProviderUrl
	} from '$lib/utils';

	type HeroMedia = {
		id?: string | null;
		name: string;
		year: number | null;
		tagline?: string | null;
		overview: string;
		genres?: string[];
		runtime?: number | null;
		release_date?: string | null;
		metadata_provider: string;
		external_id: number;
		metadata_updated_at?: string | null;
		images?: Record<string, string> | null;
		trailer_url?: string | null;
		imdb_id?: string | null;
	};

	let {
		media,
		isShow,
		actions,
		children
	}: {
		media: HeroMedia;
		/** Whether to build metadata-provider links/labels as a TV show rather than a movie. */
		isShow: boolean;
		/** Download/admin controls, rendered next to the title, right-aligned. */
		actions?: Snippet;
		/** Additional cards, rendered below the Overview card inside the same layout. */
		children?: Snippet;
	} = $props();

	let showBackdrop = $derived(media.images?.backdrop != null);
	let releaseDateLabel = $derived(formatReleaseDate(media.release_date));
	let runtimeLabel = $derived(formatRuntime(media.runtime));
	let lastUpdatedLabel = $derived(formatLastUpdated(media.metadata_updated_at));
	let providerUrl = $derived(
		getMetadataProviderUrl(media.metadata_provider, media.external_id, isShow)
	);
	let providerLabel = $derived(getMetadataProviderLabel(media.metadata_provider));
	let imdbUrl = $derived(media.imdb_id ? `https://www.imdb.com/title/${media.imdb_id}/` : null);

	// Drives both the header's white-text-on-image styling and hiding the
	// mobile logo: both only make sense while a backdrop is actually showing.
	const setHeroHeader: (active: boolean) => void = getContext('setHeroHeader');
	$effect(() => {
		setHeroHeader(showBackdrop);
		return () => setHeroHeader(false);
	});
</script>

<svelte:head>
	<title>{getFullyQualifiedMediaName(media)} - MediaManager</title>
	<meta
		content="View details and manage downloads for {getFullyQualifiedMediaName(
			media
		)} in MediaManager"
		name="description"
	/>
</svelte:head>

{#if showBackdrop}
	<div
		class="relative -mt-16 h-56 w-full overflow-hidden bg-muted/50 sm:h-72 md:h-96 md:rounded-t-xl"
	>
		<MediaImage {media} variant="backdrop" />
		<div
			class="pointer-events-none absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-black/65 to-transparent sm:h-32"
		></div>
	</div>
{/if}
<div class="mx-auto w-full px-4 md:max-w-[80em]">
	<div class="relative z-10 mt-4 mb-4 flex flex-col gap-6 sm:flex-row sm:items-start">
		<div
			class={cn(
				'relative aspect-2/3 w-28 shrink-0 overflow-hidden rounded-lg shadow-lg ring-1 ring-border sm:w-40 md:w-48 lg:w-52',
				showBackdrop && '-mt-12 sm:-mt-16 md:-mt-20'
			)}
		>
			<MediaImage {media} />
		</div>
		<div class="mt-4 flex min-w-0 flex-1 flex-col gap-2">
			<div class="flex items-start gap-x-8">
				<h1
					class="min-w-0 flex-1 scroll-m-20 text-left text-4xl font-extrabold tracking-tight lg:text-5xl"
				>
					{media.name}
					{#if media.year != null}
						<span class="font-light">
							({media.year})
						</span>
					{/if}
				</h1>
				{#if actions}
					<div class="flex h-10 shrink-0 items-center gap-2 lg:h-12">
						{@render actions()}
					</div>
				{/if}
			</div>
			{#if media.tagline}
				<p class="text-medium text-lg text-muted-foreground italic">{media.tagline}</p>
			{/if}
			<div class="flex flex-wrap items-center gap-x-3 gap-y-2 text-sm text-muted-foreground">
				{#if releaseDateLabel}
					<span>{releaseDateLabel}</span>
				{/if}
				{#if runtimeLabel}
					<span>{runtimeLabel}</span>
				{/if}
				{#if media.genres && media.genres.length > 0}
					<div class="flex flex-wrap gap-1">
						{#each media.genres as genre (genre)}
							<Badge variant="secondary">{genre}</Badge>
						{/each}
					</div>
				{/if}
			</div>
			{#if media.trailer_url || imdbUrl || providerUrl}
				<div class="flex flex-wrap items-center gap-2">
					{#if media.trailer_url}
						<Button
							variant="outline"
							size="sm"
							href={media.trailer_url}
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
			{/if}
		</div>
	</div>
</div>
<main class="mx-auto flex w-full flex-1 flex-col gap-4 p-4 md:max-w-[80em]">
	<Card.Root class="flex w-full flex-col">
		<Card.Content class="flex flex-col gap-3">
			<p class="text-justify text-sm leading-6 hyphens-auto text-muted-foreground">
				{media.overview}
			</p>
			{#if providerUrl}
				<p class="text-xs text-muted-foreground">
					Source:
					<a
						href={providerUrl}
						target="_blank"
						rel="noopener noreferrer external"
						class="underline hover:text-foreground"
					>
						{getMetadataProviderLabel(media.metadata_provider)}
					</a>
					{#if lastUpdatedLabel}
						· Last updated: {lastUpdatedLabel}
					{/if}
				</p>
			{/if}
		</Card.Content>
	</Card.Root>
	{@render children?.()}
</main>
