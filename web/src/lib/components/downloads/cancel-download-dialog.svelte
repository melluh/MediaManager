<script lang="ts">
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import { buttonVariants } from '$lib/components/ui/button/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { invalidateAll } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import client from '$lib/api';
	import type { TorrentWithProgress } from '$lib/api/api';

	let { torrent, open = $bindable() }: { torrent: TorrentWithProgress; open: boolean } = $props();

	let removeFromClient = $state(false);
	let cancelling = $state(false);

	async function cancelDownload() {
		cancelling = true;
		const { error } = await client.POST('/api/v1/torrent/{torrent_id}/cancel', {
			params: {
				path: { torrent_id: torrent.id! },
				query: { remove_from_client: removeFromClient }
			}
		});
		cancelling = false;

		if (error) {
			toast.error('Failed to cancel the download.');
			return;
		}

		open = false;
		toast.success('Download cancelled.');
		await invalidateAll();
	}
</script>

<AlertDialog.Root bind:open>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Cancel this download?</AlertDialog.Title>
			<AlertDialog.Description>
				This removes the download from your homepage. It stays on record as cancelled, so it won't
				be re-imported automatically.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<div class="flex items-start space-x-2 py-2">
			<Checkbox bind:checked={removeFromClient} id="remove-from-client" class="mt-0.5" />
			<Label
				for="remove-from-client"
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
			<AlertDialog.Cancel disabled={cancelling}>Keep downloading</AlertDialog.Cancel>
			<AlertDialog.Action
				onclick={(e) => {
					e.preventDefault();
					cancelDownload();
				}}
				disabled={cancelling}
				class={buttonVariants({ variant: 'destructive' })}
			>
				{#if cancelling}
					<LoaderCircle class="animate-spin" />
				{:else}
					<CircleX />
				{/if}
				Cancel Download
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
