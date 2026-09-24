<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import type { MetaDataProviderSearchResult } from '$lib/api/api';
	import ExternalPosterImage from '$lib/components/external-poster-image.svelte';
	import AddMediaDialog from '$lib/components/add-media-dialog/add-media-dialog.svelte';
	import MediaCard from '$lib/components/media-card.svelte';
	import { fetchMediaDetailsCached } from '$lib/api/media-details';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';

	let posterImageLoaded = $state(false);
	let { result, isShow = true }: { result: MetaDataProviderSearchResult; isShow: boolean } =
		$props();
	const hasPoster = $derived((result.poster_images?.length ?? 0) > 0);
	const detailsDialog = $derived(
		shallowDialog(`addMedia:${result.metadata_provider}-${result.media_type}-${result.external_id}`)
	);

	// Warm the details cache on hover/focus so the dialog's fetch (~1s) is
	// often already in flight or done by the time the user clicks.
	let prefetched = false;
	function prefetchDetails() {
		if (prefetched) return;
		prefetched = true;
		fetchMediaDetailsCached(result, isShow);
	}
</script>

<Dialog.Root bind:open={detailsDialog.open}>
	<Dialog.Trigger>
		{#snippet child({ props })}
			<MediaCard
				name={result.name}
				year={result.year}
				runtime={result.runtime}
				genres={result.genres}
				posterLoaded={posterImageLoaded}
				{hasPoster}
				triggerProps={{ ...props, onmouseenter: prefetchDetails, onfocus: prefetchDetails }}
			>
				{#snippet poster()}
					<ExternalPosterImage
						className="h-full w-full object-cover"
						posterImages={result.poster_images ?? []}
						alt={`${result.name}'s Poster Image`}
						bind:loaded={posterImageLoaded}
					/>
				{/snippet}
			</MediaCard>
		{/snippet}
	</Dialog.Trigger>
	<AddMediaDialog {result} {isShow} open={detailsDialog.open} />
</Dialog.Root>
