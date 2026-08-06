<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import ImageOff from '@lucide/svelte/icons/image-off';
	import type { MetaDataProviderSearchResult } from '$lib/api/api';
	import ExternalPosterImage from '$lib/components/external-poster-image.svelte';
	import AddMediaDialog from '$lib/components/add-media-dialog/add-media-dialog.svelte';
	import MediaCard from '$lib/components/media-card.svelte';
	import { fetchMediaDetailsCached } from '$lib/api/media-details';

	let detailsOpen = $state(false);
	let posterImageLoaded = $state(false);
	let { result, isShow = true }: { result: MetaDataProviderSearchResult; isShow: boolean } =
		$props();

	// Warm the details cache on hover/focus so the dialog's fetch (~1s) is
	// often already in flight or done by the time the user clicks.
	let prefetched = false;
	function prefetchDetails() {
		if (prefetched) return;
		prefetched = true;
		fetchMediaDetailsCached(result, isShow);
	}
</script>

<Dialog.Root bind:open={detailsOpen}>
	<Dialog.Trigger>
		{#snippet child({ props })}
			<MediaCard
				name={result.name}
				year={result.year}
				runtime={result.runtime}
				genres={result.genres}
				posterLoaded={posterImageLoaded}
				triggerProps={{ ...props, onmouseenter: prefetchDetails, onfocus: prefetchDetails }}
			>
				{#snippet poster()}
					{#if (result.poster_images?.length ?? 0) > 0}
						<ExternalPosterImage
							className="h-full w-full object-cover"
							posterImages={result.poster_images ?? []}
							alt={`${result.name}'s Poster Image`}
							bind:loaded={posterImageLoaded}
						/>
					{:else}
						<div class="flex h-full w-full items-center justify-center bg-muted">
							<ImageOff class="h-12 w-12 text-gray-400" />
						</div>
					{/if}
				{/snippet}
			</MediaCard>
		{/snippet}
	</Dialog.Trigger>
	<AddMediaDialog {result} {isShow} open={detailsOpen} />
</Dialog.Root>
