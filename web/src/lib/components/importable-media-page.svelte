<script lang="ts">
	import type { MediaImportSuggestion } from '$lib/api/api';
	import { setCrumbs } from '$lib/context.svelte';
	import { rescanImportableMedia, importMatchedMedia } from '$lib/api/importable';
	import { invalidateAll } from '$app/navigation';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Spinner } from '$lib/components/ui/spinner';
	import * as Table from '$lib/components/ui/table/index.js';
	import ImportableMediaRow, {
		type BulkImportStatus
	} from '$lib/components/import-media/importable-media-row.svelte';
	import { getConfidenceMeta } from '$lib/components/import-media/confidence';
	import PageHeading from '$lib/components/page-heading.svelte';
	import RescanButton from '$lib/components/import-media/rescan-button.svelte';
	import Download from '@lucide/svelte/icons/download';
	import { toast } from 'svelte-sonner';
	import PageLoading from '$lib/components/page-loading.svelte';
	import { SvelteSet } from 'svelte/reactivity';

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
		importable: Promise<MediaImportSuggestion[]>;
		emptyMessage: string;
	} = $props();

	setCrumbs(() => [{ label: parentCrumbLabel, href: parentCrumbHref }, { label: crumb }]);

	let isRescanning = $state(false);

	async function rescan() {
		isRescanning = true;
		const failed = await rescanImportableMedia(isShow);
		if (failed) {
			toast.error('Failed to rescan for importable media');
		}
		isRescanning = false;
		selected.clear();
	}

	let selected = new SvelteSet<string>();
	let isBulkImporting = $state(false);
	let bulkStatuses = $state<Record<string, BulkImportStatus>>({});

	function toggleSelected(directory: string, value: boolean) {
		if (value) {
			selected.add(directory);
		} else {
			selected.delete(directory);
		}
	}

	function deselectAll() {
		selected.clear();
	}

	// Runs sequentially so the UI can show one row importing at a time; each
	// import skips its own reload (see `importMatchedMedia`) so the list
	// doesn't shrink out from under the batch mid-run. The list is reloaded
	// once, after the whole batch finishes.
	async function startBulkImport(rows: MediaImportSuggestion[]) {
		const targets = (
			selected.size > 0 ? rows.filter((row) => selected.has(row.directory)) : rows
		).filter((row) => row.match);
		if (targets.length === 0) return;

		isBulkImporting = true;
		bulkStatuses = Object.fromEntries(targets.map((row) => [row.directory, 'waiting']));

		let failures = 0;
		for (const row of targets) {
			bulkStatuses = { ...bulkStatuses, [row.directory]: 'importing' };
			const failed = await importMatchedMedia(isShow, row.match!, row.directory, {
				invalidate: false
			});
			if (failed) failures++;
			bulkStatuses = { ...bulkStatuses, [row.directory]: failed ? 'error' : 'success' };
		}

		await invalidateAll();

		if (failures === 0) {
			toast.success(
				`Imported ${targets.length} ${targets.length === 1 ? 'directory' : 'directories'}`
			);
		} else {
			toast.error(`Failed to import ${failures} of ${targets.length} directories`);
		}

		isBulkImporting = false;
		bulkStatuses = {};
		selected.clear();
	}

	function countNeedingAttention(media: MediaImportSuggestion[]): number {
		return media.filter((suggestion) => getConfidenceMeta(suggestion.confidence).needsAttention)
			.length;
	}

	/**
	 * Least certain first, so a library with hundreds of directories opens on the
	 * handful the user actually has to decide about. `sort` is stable, so equally
	 * rated directories keep the order the scan returned them in.
	 */
	function sortedSuggestions(media: MediaImportSuggestion[]): MediaImportSuggestion[] {
		return [...media].sort(
			(a, b) => getConfidenceMeta(a.confidence).rank - getConfidenceMeta(b.confidence).rank
		);
	}

	function summarize(total: number, needingAttention: number): string {
		const directories = `${total} ${total === 1 ? 'directory' : 'directories'} detected`;
		if (needingAttention === 0) return '';
		if (needingAttention === 1) return `${directories}. 1 is not an exact match.`;
		return `${directories}. ${needingAttention} are not exact matches.`;
	}
</script>

<svelte:head>
	<title>{title} - MediaManager</title>
	<meta content={description} name="description" />
</svelte:head>

<main class="flex w-full flex-1 flex-col gap-4 p-4 pt-0">
	<PageHeading>{title}</PageHeading>
	{#await importable}
		<PageLoading message="Loading importable media…" />
	{:then media}
		{@const needingAttention = countNeedingAttention(media)}
		{@const rows = sortedSuggestions(media)}
		{@const matchedCount = rows.filter((row) => row.match).length}
		<div class="flex flex-wrap items-center justify-between gap-2">
			<div class="flex flex-wrap items-center gap-4">
				{#if media.length > 0}
					<RescanButton rescanning={isRescanning} onclick={rescan} />
				{/if}
				<p class="text-sm text-muted-foreground">{summarize(media.length, needingAttention)}</p>
			</div>
			<div class="flex flex-wrap items-center gap-2">
				{#if selected.size > 0}
					<Button variant="outline" size="sm" onclick={deselectAll} disabled={isBulkImporting}>
						Deselect all
					</Button>
				{/if}
				{#if matchedCount > 0}
					<Button size="sm" onclick={() => startBulkImport(rows)} disabled={isBulkImporting}>
						{#if isBulkImporting}
							<Spinner class="size-4" />
						{:else}
							<Download class="size-4" />
						{/if}
						{selected.size > 0 ? `Import selected (${selected.size})` : 'Import all'}
					</Button>
				{/if}
			</div>
		</div>
		{#if media.length > 0}
			<div class="w-full overflow-x-auto rounded-md border">
				<Table.Root>
					<Table.Header>
						<Table.Row>
							<Table.Head></Table.Head>
							<Table.Head>Directory</Table.Head>
							<Table.Head>Matched {isShow ? 'show' : 'movie'}</Table.Head>
							<Table.Head>Confidence</Table.Head>
							<Table.Head class="text-right">Actions</Table.Head>
						</Table.Row>
					</Table.Header>
					<Table.Body>
						{#each rows as suggestion (suggestion.directory)}
							<ImportableMediaRow
								{suggestion}
								{isShow}
								selected={selected.has(suggestion.directory)}
								onSelectedChange={(value) => toggleSelected(suggestion.directory, value)}
								bulkStatus={bulkStatuses[suggestion.directory] ?? null}
							/>
						{/each}
					</Table.Body>
				</Table.Root>
			</div>
		{:else}
			<div class="flex flex-1 flex-col items-center justify-center gap-4 text-center">
				<p class="text-muted-foreground">{emptyMessage}</p>
				<RescanButton rescanning={isRescanning} onclick={rescan} />
			</div>
		{/if}
	{/await}
</main>
