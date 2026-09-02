<script lang="ts">
	import { Button, type ButtonSize } from '$lib/components/ui/button';
	import * as Dialog from '$lib/components/ui/dialog';
	import FilePathSuffixSelector from '$lib/components/download-dialogs/file-path-suffix-selector.svelte';
	import type { Movie, Show } from '$lib/api/api';
	import { type Snippet } from 'svelte';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';

	let {
		filePathSuffix = $bindable(),
		media,
		callback,
		dialogKey,
		triggerIcon,
		triggerText = 'Download',
		size,
		disabled = false
	}: {
		filePathSuffix: string;
		media: Movie | Show;
		callback: () => void;
		/** Unique among the other dialogs open at the same time (e.g. sibling rows). */
		dialogKey: string;
		triggerIcon?: Snippet;
		triggerText?: string;
		size?: ButtonSize;
		disabled?: boolean;
	} = $props();
	const dialogState = $derived(shallowDialog(`selectFilePathSuffix:${dialogKey}`));

	function onDownload() {
		callback();
		dialogState.open = false;
	}
</script>

<Dialog.Root bind:open={() => dialogState.open, (v) => (dialogState.open = v)}>
	<Dialog.Trigger>
		<Button class="w-full" {size} {disabled} onclick={() => (dialogState.open = true)}>
			{#if triggerIcon}{@render triggerIcon()}{/if}
			{triggerText}
		</Button>
	</Dialog.Trigger>
	<Dialog.Content class="w-full max-w-[600px] rounded-lg p-6 shadow-lg">
		<Dialog.Header>
			<Dialog.Title class="mb-1 text-xl font-semibold">Set File Path Suffix</Dialog.Title>
			<Dialog.Description class="mb-4 text-sm">
				Set the filepath suffix for downloaded files of the torrent.
			</Dialog.Description>
		</Dialog.Header>
		<FilePathSuffixSelector bind:filePathSuffix {media} />
		<div class="mt-8 flex justify-between gap-2">
			<Button onclick={() => (dialogState.open = false)} variant="secondary">Cancel</Button>
			<Button onclick={() => onDownload()}>Download Torrent</Button>
		</div>
	</Dialog.Content>
</Dialog.Root>
