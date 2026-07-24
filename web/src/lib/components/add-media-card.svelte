<script lang="ts">
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { ChevronRight, ImageOff } from 'lucide-svelte';
	import type { MetaDataProviderSearchResult } from '$lib/api/api';
	import ExternalPosterImage from '$lib/components/external-poster-image.svelte';
	import AddMediaDialog from '$lib/components/add-media-dialog.svelte';
	import { formatRuntime } from '$lib/utils';

	let detailsOpen = $state(false);
	let { result, isShow = true }: { result: MetaDataProviderSearchResult; isShow: boolean } =
		$props();
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
		<AddMediaDialog {result} {isShow} open={detailsOpen} />
	</Dialog.Root>
</Card.Root>
