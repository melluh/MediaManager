<script lang="ts">
	import type { PublicMovie, PublicShow } from '$lib/api/api.ts';
	import { toast } from 'svelte-sonner';
	import client from '$lib/api/index.ts';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { getFullyQualifiedMediaName } from '$lib/utils.ts';
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { buttonVariants } from '$lib/components/ui/button/index.js';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';

	let {
		media,
		isShow
	}: {
		media: PublicMovie | PublicShow;
		isShow: boolean;
	} = $props();
	const deleteDialog = shallowDialog('deleteMedia');
	let deleteFilesOnDisk = $state(false);
	let deleteTorrents = $state(false);

	// Deletion navigates away on success, which replaces the page (and its
	// shallow-routed state) anyway, so we don't close the dialog ourselves.
	async function delete_movie() {
		if (!media.id) {
			toast.error('Movie ID is missing');
			return;
		}
		const { error } = await client.DELETE('/api/v1/movies/{movie_id}', {
			params: {
				path: { movie_id: media.id },
				query: { delete_files_on_disk: deleteFilesOnDisk, delete_torrents: deleteTorrents }
			}
		});
		if (error) {
			toast.error('Failed to delete movie: ' + error.detail);
		} else {
			toast.success('Movie deleted successfully.');
			await goto(resolve('/dashboard/movies', {}), { invalidateAll: true });
		}
	}

	async function delete_show() {
		const { error } = await client.DELETE('/api/v1/tv/shows/{show_id}', {
			params: {
				path: { show_id: media.id! },
				query: { delete_files_on_disk: deleteFilesOnDisk, delete_torrents: deleteTorrents }
			}
		});
		if (error) {
			toast.error('Failed to delete show: ' + error.detail);
		} else {
			toast.success('Show deleted successfully.');
			await goto(resolve('/dashboard/tv', {}), { invalidateAll: true });
		}
	}
</script>

<AlertDialog.Root bind:open={() => deleteDialog.open, (v) => (deleteDialog.open = v)}>
	<AlertDialog.Trigger>
		{#snippet child({ props })}
			<DropdownMenu.Item
				{...props}
				closeOnSelect={false}
				class="text-destructive data-[highlighted]:bg-destructive/10 data-[highlighted]:text-destructive"
			>
				<Trash2 />
				Delete
			</DropdownMenu.Item>
		{/snippet}
	</AlertDialog.Trigger>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Delete {getFullyQualifiedMediaName(media)}?</AlertDialog.Title>
			<AlertDialog.Description>
				This action cannot be undone. This will permanently delete
				<strong>{getFullyQualifiedMediaName(media)}</strong>.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<div class="flex flex-col gap-4 py-4">
			<div class="flex items-center space-x-2">
				<Checkbox bind:checked={deleteFilesOnDisk} id="delete-files" />
				<Label
					for="delete-files"
					class="text-sm leading-none font-medium peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
				>
					Delete media files from my library<br />
					<span class="text-sm text-muted-foreground"
						>Deletes the imported copy from your media library folder. Files still sitting in your
						download client are unaffected by this.</span
					>
				</Label>
			</div>
			<div class="flex items-center space-x-2">
				<Checkbox bind:checked={deleteTorrents} id="delete-torrents" />
				<Label
					for="delete-torrents"
					class="text-sm leading-none font-medium peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
				>
					Delete torrents from my download client<br />
					<span class="text-sm text-muted-foreground"
						>Removes the torrent from your download client and deletes the data it downloaded there.</span
					>
				</Label>
			</div>
		</div>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
			<AlertDialog.Action
				onclick={() => {
					if (isShow) {
						delete_show();
					} else delete_movie();
				}}
				class={buttonVariants({ variant: 'destructive' })}
			>
				<Trash2 />
				Delete
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
