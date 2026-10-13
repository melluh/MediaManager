<script lang="ts">
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import { buttonVariants } from '$lib/components/ui/button/index.js';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import { toast } from 'svelte-sonner';
	import client from '$lib/api';
	import type { MediaFile } from '$lib/components/media-file-details-dialog.svelte';

	let {
		file,
		open = $bindable(),
		onDeleted
	}: {
		file: MediaFile;
		open: boolean;
		onDeleted?: () => void;
	} = $props();

	let deleting = $state(false);

	async function deleteFile() {
		deleting = true;
		const query = { file_path_suffix: file.file_path_suffix };
		const { error } =
			'movie_id' in file
				? await client.DELETE('/api/v1/movies/{movie_id}/files', {
						params: { path: { movie_id: file.movie_id }, query }
					})
				: await client.DELETE('/api/v1/tv/episodes/{episode_id}/files', {
						params: { path: { episode_id: file.episode_id }, query }
					});
		deleting = false;

		if (error) {
			toast.error(
				'Failed to delete the file: ' +
					(error?.detail ? String(error.detail) : 'Please try again later.')
			);
			return;
		}

		open = false;
		toast.success('File deleted.');
		onDeleted?.();
	}
</script>

<AlertDialog.Root bind:open>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Delete this file?</AlertDialog.Title>
			<AlertDialog.Description>
				This permanently deletes the file from disk, along with any subtitle files next to it, and
				removes it from MediaManager. This can't be undone.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<p class="font-mono text-sm break-all">{file.file_path || file.relative_path}</p>
		<AlertDialog.Footer>
			<AlertDialog.Cancel disabled={deleting}>Keep it</AlertDialog.Cancel>
			<AlertDialog.Action
				onclick={(e) => {
					e.preventDefault();
					deleteFile();
				}}
				disabled={deleting}
				class={buttonVariants({ variant: 'destructive' })}
			>
				{#if deleting}
					<LoaderCircle class="animate-spin" />
				{:else}
					<Trash2 />
				{/if}
				Delete File
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
