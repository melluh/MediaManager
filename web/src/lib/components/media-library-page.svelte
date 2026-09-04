<script lang="ts">
	import LibraryMediaCard from '$lib/components/library-media-card.svelte';
	import MediaCardSkeleton from '$lib/components/media-card-skeleton.svelte';
	import MediaLibraryFilters from '$lib/components/media-library-filters.svelte';
	import type { MediaImportSuggestion, MovieListItem, ShowSummary, UserRead } from '$lib/api/api';
	import { getContext } from 'svelte';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';
	import { importablePath, rescanImportableMedia } from '$lib/api/importable';
	import PageLoadError from '$lib/components/page-load-error.svelte';
	import { Button, buttonVariants } from '$lib/components/ui/button/index.js';
	import { Spinner } from '$lib/components/ui/spinner';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import FolderInput from '@lucide/svelte/icons/folder-input';
	import EllipsisVertical from '@lucide/svelte/icons/ellipsis-vertical';
	import { toast } from 'svelte-sonner';
	import { defaultMediaLibraryFilters, filterAndSortMedia } from '$lib/utils';

	let {
		isShow,
		title,
		crumb,
		description,
		items,
		importable,
		emptyMessage
	}: {
		isShow: boolean;
		title: string;
		crumb: string;
		description: string;
		items: Promise<(ShowSummary | MovieListItem)[] | undefined>;
		importable: Promise<MediaImportSuggestion[]>;
		emptyMessage: string;
	} = $props();

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	setCrumbs([{ label: crumb }]);

	let user: () => UserRead = getContext('user');
	let isRescanning = $state(false);

	let filters = $state(defaultMediaLibraryFilters());

	let resolvedItems: (ShowSummary | MovieListItem)[] | undefined = $state(undefined);
	let loadError: string | undefined = $state(undefined);

	$effect(() => {
		resolvedItems = undefined;
		loadError = undefined;
		items
			.then((data) => {
				resolvedItems = data ?? [];
			})
			.catch((error) => {
				loadError = error instanceof Error ? error.message : String(error);
			});
	});

	let filteredItems = $derived(
		resolvedItems ? filterAndSortMedia(resolvedItems, filters) : undefined
	);

	function importableLabel(count: number): string {
		const noun = isShow ? 'show' : 'movie';
		return `${count} importable ${noun}${count === 1 ? '' : 's'}`;
	}

	async function rescan() {
		isRescanning = true;
		const failed = await rescanImportableMedia(isShow);
		if (failed) {
			toast.error('Failed to rescan for importable media');
		}
		isRescanning = false;
	}
</script>

<svelte:head>
	<title>{title} - MediaManager</title>
	<meta content={description} name="description" />
</svelte:head>

<main class="flex w-full flex-1 flex-col gap-4 p-4 pt-0">
	<h1 class="scroll-m-20 text-center text-4xl font-extrabold tracking-tight lg:text-5xl">
		{title}
	</h1>
	{#if (resolvedItems && resolvedItems.length > 0) || user()?.is_superuser}
		{#snippet noImportableDropdown()}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger
					class={buttonVariants({ variant: 'outline', size: 'icon' })}
					disabled={isRescanning}
				>
					{#if isRescanning}
						<Spinner class="size-4" />
					{:else}
						<EllipsisVertical class="size-4" />
					{/if}
					<span class="sr-only">Importable media options</span>
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end">
					<DropdownMenu.Item disabled>
						<FolderInput class="text-muted-foreground" />
						No importable {isShow ? 'shows' : 'movies'} found
					</DropdownMenu.Item>
					<DropdownMenu.Item onclick={rescan} disabled={isRescanning}>
						<RefreshCw class="text-muted-foreground" />
						Rescan
					</DropdownMenu.Item>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		{/snippet}
		<div class="flex flex-wrap items-center gap-2">
			{#if resolvedItems && resolvedItems.length > 0}
				<MediaLibraryFilters
					items={resolvedItems}
					{isShow}
					bind:sortBy={filters.sortBy}
					bind:selectedGenres={filters.genres}
					bind:downloadedFilter={filters.downloaded}
					bind:selectedQualities={filters.qualities}
				/>
			{/if}
			{#if user()?.is_superuser}
				<div class="ms-auto">
					{#await importable}
						{@render noImportableDropdown()}
					{:then media}
						{#if media.length > 0}
							<Button
								variant="default"
								size="default"
								href={importablePath(isShow)}
								class="relative shadow-lg"
							>
								<span
									class="absolute -top-1 -right-1 size-3 rounded-full bg-red-500 ring-2 ring-background"
								></span>
								<FolderInput class="size-4" />
								{importableLabel(media.length)}
							</Button>
						{:else}
							{@render noImportableDropdown()}
						{/if}
					{/await}
				</div>
			{/if}
		</div>
	{/if}
	{#if loadError}
		<PageLoadError title={`${isShow ? 'TV shows' : 'Movies'} unavailable`} message={loadError} />
	{:else if resolvedItems === undefined}
		<div
			class="grid w-full auto-rows-min gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5"
		>
			{#each { length: 10 }}
				<MediaCardSkeleton />
			{/each}
		</div>
	{:else}
		<div
			class="grid w-full auto-rows-min gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5"
		>
			{#each filteredItems ?? [] as item (item.id)}
				<LibraryMediaCard media={item} {isShow} />
			{:else}
				<div class="col-span-full text-center text-muted-foreground">
					{resolvedItems.length === 0 ? emptyMessage : 'No media matches the selected filters.'}
				</div>
			{/each}
		</div>
	{/if}
</main>
