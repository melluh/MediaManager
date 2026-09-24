<script lang="ts">
	import Film from '@lucide/svelte/icons/film';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import type { HeroMedia } from '$lib/components/media-hero-header.svelte';
	import {
		formatRuntime,
		formatReleaseDate,
		getMetadataProviderLabel,
		getMetadataProviderUrl,
		getLanguageDisplayName
	} from '$lib/utils';

	let { media, isShow }: { media: HeroMedia; isShow: boolean } = $props();

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

	// Browsers can't shrink-wrap wrapped text, so a max-width on the genres
	// cell leaves a gap next to its label. Instead, break the list into lines
	// ourselves and never let a line wrap, so the cell hugs its widest line.
	const GENRE_LINE_MAX_CHARS = 28;
	let genreLines = $derived.by(() => {
		const lines: string[][] = [];
		let length = 0;
		for (const genre of media.genres ?? []) {
			const current = lines.at(-1);
			if (current && length + genre.length + 2 <= GENRE_LINE_MAX_CHARS) {
				current.push(genre);
				length += genre.length + 2;
			} else {
				lines.push([genre]);
				length = genre.length;
			}
		}
		return lines;
	});
</script>

<dl
	class="grid min-w-0 grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm md:ml-auto [&_dd]:min-w-0 [&_dd]:text-right [&_dt]:text-muted-foreground"
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
		<dd class="flex flex-col">
			{#each genreLines as line, i (i)}
				<span class="whitespace-nowrap"
					>{line.join(', ')}{i < genreLines.length - 1 ? ',' : ''}</span
				>
			{/each}
		</dd>
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
		<dd class="flex flex-wrap justify-end gap-x-3">
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
