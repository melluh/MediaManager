<script lang="ts">
	import * as Table from '$lib/components/ui/table';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import DownloadDetailsDialog, {
		downloadDetailsDialog
	} from '$lib/components/downloads/download-details-dialog.svelte';
	import { getDownloadStatusBadge } from '$lib/components/downloads/download-status.js';
	import type { TorrentWithProgress } from '$lib/api/api';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Magnet from '@lucide/svelte/icons/magnet';
	import { formatAddedTime, formatBytes, formatTorrentSeasonEpisodeRange } from '$lib/utils';

	let {
		torrents,
		emptyTitle = 'No torrents found',
		emptyDescription = 'Torrents appear here once a download is started.',
		onChange
	}: {
		torrents: TorrentWithProgress[];
		/** Shown in place of the table when there are no torrents. */
		emptyTitle?: string;
		emptyDescription?: string;
		/** Called after a download was changed from its details dialog. */
		onChange?: () => void;
	} = $props();
</script>

{#if torrents.length === 0}
	<EmptyState icon={Magnet} title={emptyTitle}>{emptyDescription}</EmptyState>
{:else}
	<Table.Root>
		<Table.Header>
			<Table.Row>
				<Table.Head>Name</Table.Head>
				<Table.Head>Slot</Table.Head>
				<Table.Head>Size</Table.Head>
				<Table.Head>Added</Table.Head>
				<Table.Head>Status</Table.Head>
			</Table.Row>
		</Table.Header>
		<Table.Body>
			{#each torrents as torrent (torrent.id)}
				{@const statusBadge = getDownloadStatusBadge(torrent)}
				{@const detailsDialog = downloadDetailsDialog(torrent.id!)}
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
								<Table.Cell>{torrent.slot ?? '—'}</Table.Cell>
								<Table.Cell>{formatBytes(torrent.download_progress?.total_bytes) ?? '—'}</Table.Cell
								>
								<Table.Cell>{formatAddedTime(torrent.initiated_at) ?? '—'}</Table.Cell>
								<Table.Cell>
									<Badge variant={statusBadge.variant} class="w-fit shrink-0">
										<statusBadge.icon class="mr-1 size-3" />
										{statusBadge.label}
									</Badge>
								</Table.Cell>
							</Table.Row>
						{/snippet}
					</Dialog.Trigger>
					<DownloadDetailsDialog {torrent} {onChange} />
				</Dialog.Root>
			{/each}
		</Table.Body>
	</Table.Root>
{/if}
