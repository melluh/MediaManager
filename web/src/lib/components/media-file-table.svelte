<script lang="ts" generics="TFile extends MediaFile">
	import type { Snippet } from 'svelte';
	import * as Table from '$lib/components/ui/table/index.js';
	import MediaFileCells from '$lib/components/media-file-cells.svelte';
	import type { MediaFile } from '$lib/components/media-file-details-dialog.svelte';

	let {
		files,
		leadingLabel,
		leadingCell,
		emptyMessage,
		dialogKeyPrefix
	}: {
		files: TFile[];
		/** Header for the first column, which is the only media-type-specific one. */
		leadingLabel: string;
		/** Renders the first column's content for a file (file path / episode number). */
		leadingCell: Snippet<[TFile]>;
		emptyMessage: string;
		/** Must be unique per table on the page; used for the shallow-routed dialogs. */
		dialogKeyPrefix: string;
	} = $props();
</script>

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
		{:else}
			<Table.Row>
				<Table.Cell colspan={4} class="py-6 text-center font-semibold">
					{emptyMessage}
				</Table.Cell>
			</Table.Row>
		{/each}
	</Table.Body>
</Table.Root>
