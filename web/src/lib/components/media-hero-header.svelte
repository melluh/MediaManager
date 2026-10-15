<script lang="ts" module>
	export type HeroMedia = {
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
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import { getHeroHeaderSetter } from '$lib/context.svelte';
	import MediaImage from '$lib/components/media-image.svelte';
	import MediaFactsList from '$lib/components/media-facts-list.svelte';
	import { getFullyQualifiedMediaName } from '$lib/utils';

	let {
		media,
		isShow,
		actions,
		availability,
		aboveFacts,
		children
	}: {
		media: HeroMedia;
		/** Whether to build metadata-provider links/labels as a TV show rather than a movie. */
		isShow: boolean;
		/** Download/admin controls, rendered next to the title, right-aligned. */
		actions?: Snippet;
		/** Availability status, rendered under the title. Visible to every viewer, not just admins. */
		availability?: Snippet;
		/** Rendered above the facts table, at its width, e.g. the viewer's rating. */
		aboveFacts?: Snippet;
		/** Additional cards, rendered below the Overview card inside the same layout. */
		children?: Snippet;
	} = $props();

	// TV shows are shown without their year; movies keep it to disambiguate remakes.
	let pageName = $derived(isShow ? media.name : getFullyQualifiedMediaName(media));
	let showBackdrop = $derived(media.images?.backdrop != null);

	// Drives both the header's white-text-on-image styling and hiding the
	// mobile logo: both only make sense while a backdrop is actually showing.
	const setHeroHeader = getHeroHeaderSetter();
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
<div class="mx-auto w-full px-4 md:max-w-[80em] tablet:px-8">
	<div class="relative z-10 mt-4 mb-4 flex flex-col gap-6 sm:flex-row sm:items-end">
		<!-- On mobile the actions sit full-width below the title and status; from
		     md up they sit next to them, right-aligned. -->
		<div class="mt-4 flex min-w-0 flex-1 flex-col gap-8 md:flex-row md:items-start">
			<div class="flex min-w-0 flex-col gap-1.5 md:flex-1">
				<h1 class="scroll-m-20 text-left text-4xl font-extrabold tracking-tight lg:text-5xl">
					{media.name}
				</h1>
				{@render availability?.()}
			</div>
			{#if actions}
				<!-- empty:hidden: non-admins get an actions snippet that renders nothing.
				     On mobile the primary (first) action stretches to the full width. -->
				<div
					class="flex h-10 shrink-0 items-center gap-2 *:first:flex-1 empty:hidden md:*:first:flex-none lg:h-12"
				>
					{@render actions()}
				</div>
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
		<div class="flex min-w-0 flex-col gap-4 md:ml-auto">
			{@render aboveFacts?.()}
			<MediaFactsList {media} {isShow} />
		</div>
	</section>
	{@render children?.()}
</main>
