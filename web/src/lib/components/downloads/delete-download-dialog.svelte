<script lang="ts">
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import { buttonVariants } from '$lib/components/ui/button/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { toast } from 'svelte-sonner';
	import client from '$lib/api';
	import type { TorrentWithProgress } from '$lib/api/api';

	let {
		torrent,
		open = $bindable(),
		onDeleted
	}: {
		torrent: TorrentWithProgress;
		open: boolean;
		onDeleted?: () => void;
	} = $props();

	let removeFromClient = $state(false);
	let deleting = $state(false);

	async function deleteDownload() {
		deleting = true;
		// `delete_files` only removes the download from the client - the
		// downloaded data itself is never deleted.
		const { error } = await client.DELETE('/api/v1/torrent/{torrent_id}', {
			params: {
				path: { torrent_id: torrent.id! },
				query: { delete_files: removeFromClient }
			}
		});
		deleting = false;

		if (error) {
			toast.error('Failed to delete the download.');
			return;
		}

		open = false;
		toast.success('Download deleted.');
		onDeleted?.();
	}
</script>

<AlertDialog.Root bind:open>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Delete this download?</AlertDialog.Title>
			<AlertDialog.Description>
				This permanently removes the download's record from MediaManager{#if !torrent.imported},
					along with the file entries it created for its media, since it was never imported{/if}.
				Files on disk are left in place. This can't be undone.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<div class="flex items-start space-x-2 py-2">
			<Checkbox bind:checked={removeFromClient} id="delete-remove-from-client" class="mt-0.5" />
			<Label
				for="delete-remove-from-client"
				class="text-sm leading-none font-medium peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
			>
				Also remove it from the download client
				<br />
				<span class="text-sm font-normal text-muted-foreground">
					The downloaded data is left in place, only the entry in the client is removed.
				</span>
			</Label>
		</div>
		{#if removeFromClient && !torrent.usenet}
			<div
				class="flex items-start gap-2 rounded-md border border-destructive/50 bg-destructive/10 p-2 text-xs text-destructive"
			>
				<TriangleAlert class="mt-0.5 size-3.5 shrink-0" />
				<span>
					Removing an unfinished or unseeded torrent from the client may count as a Hit & Run on
					private trackers, which can lead to warnings or a ban.
				</span>
			</div>
		{/if}
		<AlertDialog.Footer>
			<AlertDialog.Cancel disabled={deleting}>Keep it</AlertDialog.Cancel>
			<AlertDialog.Action
				onclick={(e) => {
					e.preventDefault();
					deleteDownload();
				}}
				disabled={deleting}
				class={buttonVariants({ variant: 'destructive' })}
			>
				{#if deleting}
					<LoaderCircle class="animate-spin" />
				{:else}
					<Trash2 />
				{/if}
				Delete Download
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
