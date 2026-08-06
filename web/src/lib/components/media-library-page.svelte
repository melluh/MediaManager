<script lang="ts">
	import LibraryMediaCard from '$lib/components/library-media-card.svelte';
	import ImportCandidatesDialog from '$lib/components/import-media/import-candidates-dialog.svelte';
	import DetectedMediaCard from '$lib/components/import-media/detected-media-card.svelte';
	import MediaCardSkeleton from '$lib/components/media-card-skeleton.svelte';
	import type { MediaImportSuggestion, Movie, Show, UserRead } from '$lib/api/api';
	import { getContext, onMount } from 'svelte';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';
	import client from '$lib/api';

	let {
		isShow,
		title,
		crumb,
		description,
		items,
		emptyMessage
	}: {
		isShow: boolean;
		title: string;
		crumb: string;
		description: string;
		items: Promise<(Show | Movie)[] | undefined>;
		emptyMessage: string;
	} = $props();

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	setCrumbs([{ label: crumb }]);

	let user: () => UserRead = getContext('user');
	let importableMedia: MediaImportSuggestion[] = $state([]);

	onMount(() => {
		if (!user()?.is_superuser) return;
		const promise = isShow
			? client.GET('/api/v1/tv/importable')
			: client.GET('/api/v1/movies/importable');
		promise.then(({ data, error }) => {
			if (!error) {
				importableMedia = data;
			}
		});
	});
</script>

<svelte:head>
	<title>{title} - MediaManager</title>
	<meta content={description} name="description" />
</svelte:head>

<main class="flex w-full flex-1 flex-col gap-4 p-4 pt-0">
	<h1 class="scroll-m-20 text-center text-4xl font-extrabold tracking-tight lg:text-5xl">
		{title}
	</h1>
	{#if importableMedia.length > 0}
		<div
			class="grid w-full auto-rows-min gap-4 sm:grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-4"
		>
			{#each importableMedia as importable (importable.directory)}
				<DetectedMediaCard isTv={isShow} directory={importable.directory}>
					<ImportCandidatesDialog
						isTv={isShow}
						name={importable.directory}
						candidates={importable.candidates}
					>
						Import {isShow ? 'TV show' : 'movie'}
					</ImportCandidatesDialog>
				</DetectedMediaCard>
			{/each}
		</div>
	{/if}
	<div
		class="grid w-full auto-rows-min gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5"
	>
		{#await items}
			{#each { length: 10 }}
				<MediaCardSkeleton />
			{/each}
		{:then media}
			{#each media ?? [] as item (item.id)}
				<LibraryMediaCard media={item} {isShow} />
			{:else}
				<div class="col-span-full text-center text-muted-foreground">{emptyMessage}</div>
			{/each}
		{/await}
	</div>
</main>
