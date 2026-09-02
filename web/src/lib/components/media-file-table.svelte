<script lang="ts" generics="TFile extends MediaFile">
	import type { Snippet } from 'svelte';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import { buttonVariants } from '$lib/components/ui/button/index.js';
	import CheckmarkX from '$lib/components/checkmark-x.svelte';
	import MediaFileDetailsDialog, {
		type MediaFile
	} from '$lib/components/media-file-details-dialog.svelte';
	import Info from '@lucide/svelte/icons/info';
	import { getTorrentQualityString } from '$lib/utils';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';

	let {
		files,
		caption,
		leadingLabel,
		leadingCell,
		emptyMessage,
		dialogKeyPrefix
	}: {
		files: TFile[];
		caption: string;
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
	<Table.Caption>{caption}</Table.Caption>
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
			{@const detailsDialog = shallowDialog(`${dialogKeyPrefix}:${index}`)}
			<Table.Row>
				<Table.Cell>{@render leadingCell(file)}</Table.Cell>
				<Table.Cell class="w-[120px]">
					{getTorrentQualityString(file.quality)}
				</Table.Cell>
				<Table.Cell class="w-[10px] font-medium">
					<CheckmarkX state={file.imported} />
				</Table.Cell>
				<Table.Cell class="w-[10px] text-right">
					<Dialog.Root bind:open={() => detailsDialog.open, (v) => (detailsDialog.open = v)}>
						<Dialog.Trigger class={buttonVariants({ variant: 'ghost', size: 'sm' })}>
							<Info class="size-4" />
							Details
						</Dialog.Trigger>
						<MediaFileDetailsDialog {file} />
					</Dialog.Root>
				</Table.Cell>
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
