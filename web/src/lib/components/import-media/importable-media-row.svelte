<script lang="ts">
	import type { MediaImportSuggestion } from '$lib/api/api';
	import * as Table from '$lib/components/ui/table/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Spinner } from '$lib/components/ui/spinner';
	import ExternalPosterImage from '$lib/components/external-poster-image.svelte';
	import ConfidenceBadge from '$lib/components/import-media/confidence-badge.svelte';
	import ImportCandidatesDialog from '$lib/components/import-media/import-candidates-dialog.svelte';
	import { getConfidenceMeta } from '$lib/components/import-media/confidence';
	import { importMatchedMedia } from '$lib/api/importable';
	import {
		getDirectoryName,
		getFullyQualifiedMediaName,
		getMetadataProviderLabel
	} from '$lib/utils';
	import { toast } from 'svelte-sonner';
	import Download from '@lucide/svelte/icons/download';
	import Film from '@lucide/svelte/icons/film';
	import Tv from '@lucide/svelte/icons/tv';
	import Clock from '@lucide/svelte/icons/clock';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';

	export type BulkImportStatus = 'waiting' | 'importing' | 'success' | 'error';

	let {
		suggestion,
		isShow,
		selected = false,
		onSelectedChange,
		bulkStatus = null
	}: {
		suggestion: MediaImportSuggestion;
		isShow: boolean;
		selected?: boolean;
		onSelectedChange?: (selected: boolean) => void;
		bulkStatus?: BulkImportStatus | null;
	} = $props();

	const meta = $derived(getConfidenceMeta(suggestion.confidence));
	const match = $derived(suggestion.match ?? null);
	const directoryName = $derived(getDirectoryName(suggestion.directory));
	let isImporting = $state(false);

	async function importMatch() {
		if (!match) return;
		isImporting = true;
		const failed = await importMatchedMedia(isShow, match, suggestion.directory);
		isImporting = false;

		if (failed) {
			toast.error(`Failed to import "${directoryName}"`);
		} else {
			toast.success(`Imported ${getFullyQualifiedMediaName(match)}`);
		}
	}
</script>

{#snippet posterThumb()}
	<div class="relative h-[3.75rem] w-10 shrink-0 overflow-hidden rounded border bg-muted">
		<div class="absolute inset-0 flex items-center justify-center">
			{#if isShow}
				<Tv class="size-4 text-muted-foreground/60" aria-hidden="true" />
			{:else}
				<Film class="size-4 text-muted-foreground/60" aria-hidden="true" />
			{/if}
		</div>
		{#if (match?.poster_images?.length ?? 0) > 0}
			<ExternalPosterImage
				className="relative h-full w-full object-cover"
				posterImages={match?.poster_images ?? []}
				alt={`${match?.name}'s poster image`}
				sizes="40px"
			/>
		{/if}
	</div>
{/snippet}

<Table.Row class={meta.rowClass}>
	<Table.Cell class="align-middle">
		<Checkbox
			checked={selected}
			disabled={!match || bulkStatus != null}
			onCheckedChange={(v) => onSelectedChange?.(v === true)}
			aria-label={`Select ${directoryName}`}
		/>
	</Table.Cell>
	<Table.Cell class="max-w-[24rem] align-middle">
		<div
			class="w-fit max-w-full truncate rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono font-medium"
			title={suggestion.directory}
		>
			{directoryName}
		</div>
	</Table.Cell>
	<Table.Cell class="max-w-[24rem] align-middle">
		<div class="flex items-center gap-3">
			{@render posterThumb()}
			{#if match}
				<div class="min-w-0">
					<div class="truncate font-medium">{match.name}</div>
					<div class="truncate text-xs text-muted-foreground">
						{match.year ?? 'Year unknown'} · {getMetadataProviderLabel(match.metadata_provider)}
					</div>
				</div>
			{:else}
				<span class="text-sm text-muted-foreground">
					Nothing matched this directory — pick the {isShow ? 'show' : 'movie'} yourself.
				</span>
			{/if}
		</div>
	</Table.Cell>
	<Table.Cell class="align-middle">
		<ConfidenceBadge confidence={suggestion.confidence} />
	</Table.Cell>
	<Table.Cell class="align-middle">
		<div class="flex items-center justify-end gap-2">
			{#if bulkStatus === 'waiting'}
				<span class="flex items-center gap-1.5 text-sm text-muted-foreground">
					<Clock class="size-4" />
					Queued
				</span>
			{:else if bulkStatus === 'importing'}
				<span class="flex items-center gap-1.5 text-sm text-muted-foreground">
					<Spinner class="size-4" />
					Importing…
				</span>
			{:else if bulkStatus === 'success'}
				<span class="flex items-center gap-1.5 text-sm text-green-600 dark:text-green-500">
					<CircleCheck class="size-4" />
					Imported
				</span>
			{:else if bulkStatus === 'error'}
				<span class="flex items-center gap-1.5 text-sm text-red-600 dark:text-red-500">
					<TriangleAlert class="size-4" />
					Failed
				</span>
			{:else}
				<ImportCandidatesDialog
					{isShow}
					directory={suggestion.directory}
					triggerVariant={match ? 'outline' : 'default'}
				>
					{match ? 'Change match' : 'Choose a match'}
				</ImportCandidatesDialog>
				{#if match}
					<Button size="sm" onclick={importMatch} disabled={isImporting}>
						{#if isImporting}
							<Spinner class="size-4" />
						{:else}
							<Download class="size-4" />
						{/if}
						Import
					</Button>
				{/if}
			{/if}
		</div>
	</Table.Cell>
</Table.Row>
