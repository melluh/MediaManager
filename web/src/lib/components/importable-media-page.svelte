<script lang="ts">
	import ImportCandidatesDialog from '$lib/components/import-media/import-candidates-dialog.svelte';
	import DetectedMediaCard from '$lib/components/import-media/detected-media-card.svelte';
	import type { MediaImportSuggestion } from '$lib/api/api';
	import { getContext } from 'svelte';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';
	import { rescanImportableMedia } from '$lib/api/importable';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Spinner } from '$lib/components/ui/spinner';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import { toast } from 'svelte-sonner';

	let {
		isShow,
		title,
		parentCrumbLabel,
		parentCrumbHref,
		crumb,
		description,
		importable,
		emptyMessage
	}: {
		isShow: boolean;
		title: string;
		parentCrumbLabel: string;
		parentCrumbHref: string;
		crumb: string;
		description: string;
		importable: MediaImportSuggestion[];
		emptyMessage: string;
	} = $props();

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	setCrumbs([{ label: parentCrumbLabel, href: parentCrumbHref }, { label: crumb }]);

	let isRescanning = $state(false);

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
	<div class="flex justify-end">
		<Button variant="outline" size="sm" onclick={rescan} disabled={isRescanning}>
			{#if isRescanning}
				<Spinner class="size-4" />
			{:else}
				<RefreshCw class="size-4" />
			{/if}
			Rescan for importable media
		</Button>
	</div>
	{#if importable.length > 0}
		<div
			class="grid w-full auto-rows-min gap-4 sm:grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-4"
		>
			{#each importable as candidate (candidate.directory)}
				<DetectedMediaCard isTv={isShow} directory={candidate.directory}>
					<ImportCandidatesDialog
						isTv={isShow}
						name={candidate.directory}
						candidates={candidate.candidates}
					>
						Import {isShow ? 'TV show' : 'movie'}
					</ImportCandidatesDialog>
				</DetectedMediaCard>
			{/each}
		</div>
	{:else}
		<div class="text-center text-muted-foreground">{emptyMessage}</div>
	{/if}
</main>
