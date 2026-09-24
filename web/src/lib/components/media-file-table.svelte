<script lang="ts" generics="TFile extends MediaFile">
	import type { Snippet } from 'svelte';
	import * as Table from '$lib/components/ui/table/index.js';
	import MediaFileCells from '$lib/components/media-file-cells.svelte';
	import type { MediaFile } from '$lib/components/media-file-details-dialog.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import FileX from '@lucide/svelte/icons/file-x';

	let {
		files,
		leadingLabel,
		leadingCell,
		emptyTitle = 'No files found',
		emptyDescription,
		dialogKeyPrefix
	}: {
		files: TFile[];
		/** Header for the first column, which is the only media-type-specific one. */
		leadingLabel: string;
		/** Renders the first column's content for a file (file path / episode number). */
		leadingCell: Snippet<[TFile]>;
		/** Shown in place of the table when there are no files. */
		emptyTitle?: string;
		emptyDescription?: string;
		/** Must be unique per table on the page; used for the shallow-routed dialogs. */
		dialogKeyPrefix: string;
	} = $props();
</script>

{#if files.length === 0}
	{#if emptyDescription}
		<EmptyState icon={FileX} title={emptyTitle}>{emptyDescription}</EmptyState>
	{:else}
		<EmptyState icon={FileX} title={emptyTitle} />
	{/if}
{:else}
	<Table.Root>
		<Table.Header>
			<Table.Row>
				<Table.Head>{leadingLabel}</Table.Head>
				<Table.Head>Quality</Table.Head>
				<Table.Head>Imported</Table.Head>
				<Table.Head class="sr-only">Actions</Table.Head>
			</Table.Row>
		</Table.Header>
		<Table.Body>
			{#each files as file, index (file)}
				<Table.Row>
					<Table.Cell>{@render leadingCell(file)}</Table.Cell>
					<MediaFileCells {file} dialogKey={`${dialogKeyPrefix}:${index}`} />
				</Table.Row>
			{/each}
		</Table.Body>
	</Table.Root>
{/if}
