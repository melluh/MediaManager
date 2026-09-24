<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import { buttonVariants } from '$lib/components/ui/button/index.js';
	import MediaFileDetailsDialog, {
		type MediaFile
	} from '$lib/components/media-file-details-dialog.svelte';
	import Info from '@lucide/svelte/icons/info';
	import FileQuestionMark from '@lucide/svelte/icons/file-question-mark';
	import { getQualityString } from '$lib/utils';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';

	// The quality and details cells every media file table row ends with.
	let {
		file,
		dialogKey
	}: {
		file: MediaFile;
		/** Must be unique on the page; used for the shallow-routed details dialog. */
		dialogKey: string;
	} = $props();

	const detailsDialog = $derived(shallowDialog(dialogKey));
</script>

<Table.Cell class="w-[120px]">
	{getQualityString(file.details?.quality)}
</Table.Cell>
<Table.Cell class="w-[160px] text-right">
	{#if !file.exists_on_disk}
		<span class="inline-flex items-center gap-1 text-sm whitespace-nowrap text-muted-foreground">
			<FileQuestionMark class="size-4" />
			Not found on disk
		</span>
	{:else}
		<Dialog.Root bind:open={detailsDialog.open}>
			<Dialog.Trigger class={buttonVariants({ variant: 'ghost', size: 'sm' })}>
				<Info class="size-4" />
				Details
			</Dialog.Trigger>
			<MediaFileDetailsDialog {file} />
		</Dialog.Root>
	{/if}
</Table.Cell>
