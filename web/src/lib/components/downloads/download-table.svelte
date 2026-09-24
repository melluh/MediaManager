<script lang="ts">
	import * as Table from '$lib/components/ui/table';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button';
	import DownloadDetailsDialog from '$lib/components/downloads/download-details-dialog.svelte';
	import { getDownloadStatusBadge } from '$lib/components/downloads/download-status.js';
	import DeleteTorrentDialog from '$lib/components/torrents/delete-torrent-dialog.svelte';
	import EditTorrentDialog from '$lib/components/torrents/edit-torrent-dialog.svelte';
	import type { TorrentWithProgress } from '$lib/api/api';
	import { getCurrentUser } from '$lib/context.svelte';
	import client from '$lib/api';
	import { toast } from 'svelte-sonner';
	import { invalidateAll } from '$app/navigation';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';
	import {
		formatAddedTime,
		formatBytes,
		formatTorrentSeasonEpisodeRange,
		getTorrentQualityString,
		getTorrentStatusString
	} from '$lib/utils';

	let { torrents }: { torrents: TorrentWithProgress[] } = $props();

	let user = getCurrentUser();
	let columnCount = $derived(user().is_superuser ? 6 : 5);

	async function retryTorrentDownload(torrent: TorrentWithProgress) {
		const { error } = await client.POST('/api/v1/torrent/{torrent_id}/retry', {
			params: { path: { torrent_id: torrent.id! } }
		});
		if (error) {
			toast.error(`Failed on retrying download: ${error}`);
		} else {
			toast.success('Trying to download torrent...');
		}
		await invalidateAll();
	}
</script>

<Table.Root>
	<Table.Header>
		<Table.Row>
			<Table.Head>Name</Table.Head>
			<Table.Head>Quality</Table.Head>
			<Table.Head>Size</Table.Head>
			<Table.Head>Added</Table.Head>
			<Table.Head>Status</Table.Head>
			{#if user().is_superuser}
				<Table.Head class="text-right">Actions</Table.Head>
			{/if}
		</Table.Row>
	</Table.Header>
	<Table.Body>
		{#each torrents as torrent (torrent.id)}
			{@const statusBadge = getDownloadStatusBadge(torrent)}
			{@const detailsDialog = shallowDialog(`downloadDetails:${torrent.id}`)}
			{@const seasonEpisodeLabel = formatTorrentSeasonEpisodeRange(
				torrent.seasons,
				torrent.episodes
			)}
			<Dialog.Root bind:open={detailsDialog.open}>
				<Dialog.Trigger>
					{#snippet child({ props })}
						<Table.Row {...props} class="cursor-pointer">
							<Table.Cell class="font-medium">
								{torrent.title}{#if seasonEpisodeLabel}
									<span class="text-muted-foreground">&nbsp;{seasonEpisodeLabel}</span>{/if}
							</Table.Cell>
							<Table.Cell>{getTorrentQualityString(torrent.quality)}</Table.Cell>
							<Table.Cell>{formatBytes(torrent.download_progress?.total_bytes) ?? '—'}</Table.Cell>
							<Table.Cell>{formatAddedTime(torrent.initiated_at) ?? '—'}</Table.Cell>
							<Table.Cell>
								<Badge variant={statusBadge.variant} class="w-fit shrink-0">
									<statusBadge.icon class="mr-1 size-3" />
									{statusBadge.label}
								</Badge>
							</Table.Cell>
							{#if user().is_superuser}
								<Table.Cell
									class="flex flex-col justify-end gap-2 text-right xl:flex-row"
									onclick={(e) => e.stopPropagation()}
								>
									{#if getTorrentStatusString(torrent.status) !== 'finished'}
										<Button variant="secondary" onclick={() => retryTorrentDownload(torrent)}>
											Retry Download
										</Button>
									{/if}
									<DeleteTorrentDialog torrentName={torrent.title} torrentId={torrent.id!} />
									<EditTorrentDialog
										torrentId={torrent.id!}
										torrentTitle={torrent.title}
										imported={torrent.imported}
									/>
								</Table.Cell>
							{/if}
						</Table.Row>
					{/snippet}
				</Dialog.Trigger>
				<DownloadDetailsDialog {torrent} />
			</Dialog.Root>
		{:else}
			<Table.Row>
				<Table.Cell colspan={columnCount} class="text-center font-light">
					No torrents found.
				</Table.Cell>
			</Table.Row>
		{/each}
	</Table.Body>
</Table.Root>
