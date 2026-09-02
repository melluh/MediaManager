<script lang="ts">
	import { Button, buttonVariants } from '$lib/components/ui/button/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { toast } from 'svelte-sonner';
	import type { MetaDataProviderSearchResult } from '$lib/api/api';
	import { Spinner } from '$lib/components/ui/spinner';
	import SuggestedMediaCard from '$lib/components/import-media/suggested-media-card.svelte';
	import type { Snippet } from 'svelte';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';
	import { getImportCandidates, importMatchedMedia } from '$lib/api/importable';
	import { getDirectoryName } from '$lib/utils';

	let {
		isShow,
		directory,
		triggerVariant = 'default',
		children
	}: {
		isShow: boolean;
		directory: string;
		triggerVariant?: 'default' | 'outline';
		children?: Snippet;
	} = $props();

	const dialogState = $derived(shallowDialog(`importCandidates:${directory}`));
	let candidates = $state<MetaDataProviderSearchResult[] | null>(null);
	let loadFailed = $state(false);
	let isLoading = $state(false);
	let isImporting = $state(false);

	// Deliberately not `$state`: the effect below must depend on the dialog's
	// open state alone, not on the guard it writes.
	let hasRequested = false;

	async function loadCandidates() {
		isLoading = true;
		loadFailed = false;
		const results = await getImportCandidates(isShow, directory);
		candidates = results;
		loadFailed = results == null;
		isLoading = false;
	}

	// Candidates cost a metadata-provider search per directory, so they are only
	// fetched once the user actually opens the picker for this one.
	$effect(() => {
		if (dialogState.open && !hasRequested) {
			hasRequested = true;
			void loadCandidates();
		}
	});

	function retry() {
		hasRequested = true;
		void loadCandidates();
	}

	async function handleImportMedia(media: MetaDataProviderSearchResult) {
		isImporting = true;
		const failed = await importMatchedMedia(isShow, media, directory);
		isImporting = false;

		if (failed) {
			toast.error('Failed to import');
		} else {
			toast.success('Imported successfully!');
		}
		dialogState.open = false;
	}
</script>

<Dialog.Root bind:open={() => dialogState.open, (v) => (dialogState.open = v)}>
	<Dialog.Trigger
		class={buttonVariants({ variant: triggerVariant, size: 'sm' })}
		onclick={() => {
			dialogState.open = true;
		}}
	>
		{@render children?.()}
	</Dialog.Trigger>
	<Dialog.Content class="max-h-[90vh] w-fit min-w-[80vw] overflow-y-auto">
		<Dialog.Header>
			<Dialog.Title>
				Pick the {isShow ? 'show' : 'movie'} in "{getDirectoryName(directory)}"
			</Dialog.Title>
			<Dialog.Description>
				Importing replaces whatever the scan matched for
				<code class="rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono text-xs">{directory}</code>
			</Dialog.Description>
		</Dialog.Header>
		{#if isImporting || isLoading}
			<div class="flex justify-center py-12">
				<Spinner class="size-8" />
			</div>
		{:else if loadFailed}
			<div class="flex flex-col items-center gap-3 py-12">
				<p class="text-sm text-red-500">Failed to search for this directory.</p>
				<Button variant="outline" size="sm" onclick={retry}>Try again</Button>
			</div>
		{:else}
			<div
				class="grid w-full auto-rows-min gap-4 sm:grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-4"
			>
				{#each candidates ?? [] as candidate (candidate.external_id)}
					<SuggestedMediaCard result={candidate} action={() => handleImportMedia(candidate)} />
				{:else}
					<p class="col-span-full py-8 text-center text-sm text-muted-foreground">
						No {isShow ? 'shows' : 'movies'} were found, change the directory's name for better search
						results!
					</p>
				{/each}
			</div>
		{/if}
	</Dialog.Content>
</Dialog.Root>
