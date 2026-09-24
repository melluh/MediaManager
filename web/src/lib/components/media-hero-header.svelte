<script lang="ts">
	import { getContext, type Snippet } from 'svelte';
	import MediaImage from '$lib/components/media-image.svelte';
	import Film from '@lucide/svelte/icons/film';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import {
		cn,
		getFullyQualifiedMediaName,
		formatRuntime,
		formatReleaseDate,
		getMetadataProviderLabel,
		getMetadataProviderUrl,
		getLanguageDisplayName
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
		images?: Record<string, string> | null;
		trailer_url?: string | null;
		imdb_id?: string | null;
		original_language?: string | null;
		ended?: boolean;
	};

	let {
		media,
		isShow,
		actions,
		availability,
		children
	}: {
		media: HeroMedia;
		/** Whether to build metadata-provider links/labels as a TV show rather than a movie. */
		isShow: boolean;
		/** Download/admin controls, rendered next to the title, right-aligned. */
		actions?: Snippet;
		/** Availability badge(s), rendered under the title. Visible to every viewer, not just admins. */
		availability?: Snippet;
		/** Additional cards, rendered below the Overview card inside the same layout. */
		children?: Snippet;
	} = $props();

	// TV shows are shown without their year; movies keep it to disambiguate remakes.
	let pageName = $derived(isShow ? media.name : getFullyQualifiedMediaName(media));
	let showBackdrop = $derived(media.images?.backdrop != null);
	let releaseDateLabel = $derived(formatReleaseDate(media.release_date));
	let releaseYear = $derived(
		media.year ?? (media.release_date ? new Date(media.release_date).getFullYear() || null : null)
	);
	let runtimeLabel = $derived(formatRuntime(media.runtime));
	let providerUrl = $derived(
		getMetadataProviderUrl(media.metadata_provider, media.external_id, isShow)
	);
	let providerLabel = $derived(getMetadataProviderLabel(media.metadata_provider));
	let languageLabel = $derived(getLanguageDisplayName(media.original_language));
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
	<title>{pageName} - MediaManager</title>
	<meta
		content="View details and manage downloads for {pageName} in MediaManager"
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
	<div class="relative z-10 mt-4 mb-4 flex flex-col gap-6 sm:flex-row sm:items-end">
		<!-- <div
			class={cn(
				'relative aspect-2/3 w-28 shrink-0 overflow-hidden rounded-lg shadow-lg ring-1 ring-border sm:w-40 md:w-48 lg:w-52',
				showBackdrop && '-mt-12 sm:-mt-16 md:-mt-20'
			)}
		>
			<MediaImage {media} />
		</div> -->
		<div class="mt-4 flex min-w-0 flex-1 flex-col gap-2">
			<div class="flex items-start gap-x-8">
				<h1
					class="min-w-0 flex-1 scroll-m-20 text-left text-4xl font-extrabold tracking-tight lg:text-5xl"
				>
					{media.name}
				</h1>
				{#if actions}
					<div class="flex h-10 shrink-0 items-center gap-2 lg:h-12">
						{@render actions()}
					</div>
				{/if}
			</div>

			{#if availability}
				{@render availability()}
			{/if}
		</div>
	</div>
</div>
<main class="mx-auto flex w-full flex-1 flex-col gap-4 p-4 pb-16 md:max-w-[80em]">
	<section class="flex w-full flex-col gap-6 md:flex-row md:items-start md:gap-10">
		<div class="flex min-w-0 flex-1 flex-col gap-3">
			{#if media.tagline}
				<p class="text-medium text-lg text-muted-foreground italic">{media.tagline}</p>
			{/if}
			<p class="text-justify text-sm leading-6 hyphens-auto text-muted-foreground">
				{media.overview}
			</p>
		</div>
		<dl
			class="grid min-w-0 grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm md:ml-auto [&_dd]:min-w-0 [&_dt]:text-muted-foreground"
		>
			{#if releaseDateLabel || releaseYear != null}
				<dt>{isShow ? 'First aired' : 'Released'}</dt>
				<dd>{releaseDateLabel ?? releaseYear}</dd>
			{/if}
			{#if runtimeLabel}
				<dt>Runtime</dt>
				<dd>{runtimeLabel}</dd>
			{/if}
			{#if languageLabel}
				<dt>Language</dt>
				<dd>{languageLabel}</dd>
			{/if}
			{#if media.genres && media.genres.length > 0}
				<dt>{media.genres.length === 1 ? 'Genre' : 'Genres'}</dt>
				<dd>{media.genres.join(', ')}</dd>
			{/if}
			{#if isShow && media.ended != null}
				<dt>Status</dt>
				<dd>{media.ended ? 'Ended' : 'Continuing'}</dd>
			{/if}
			{#if media.trailer_url}
				<dt>Trailer</dt>
				<dd>
					<a
						href={media.trailer_url}
						target="_blank"
						rel="noopener noreferrer"
						class="inline-flex items-center gap-1 underline hover:text-foreground"
					>
						Watch trailer
						<Film class="size-3.5" />
					</a>
				</dd>
			{/if}
			{#if imdbUrl || providerUrl}
				<dt>Links</dt>
				<dd class="flex flex-wrap gap-x-3">
					{#if imdbUrl}
						<a
							href={imdbUrl}
							target="_blank"
							rel="noopener noreferrer"
							class="inline-flex items-center gap-1 underline hover:text-foreground"
						>
							IMDb
							<ExternalLink class="size-3.5" />
						</a>
					{/if}
					{#if providerUrl}
						<a
							href={providerUrl}
							target="_blank"
							rel="noopener noreferrer external"
							class="inline-flex items-center gap-1 underline hover:text-foreground"
						>
							{providerLabel}
							<ExternalLink class="size-3.5" />
						</a>
					{/if}
				</dd>
			{/if}
		</dl>
	</section>
	{@render children?.()}
</main>
