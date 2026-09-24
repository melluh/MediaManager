<script lang="ts">
	import * as Table from '$lib/components/ui/table';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import Download from '@lucide/svelte/icons/download';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import TorrentScoreValue from '$lib/components/download-dialogs/torrent-score-value.svelte';
	import { formatSize } from '$lib/components/download-dialogs/torrent-format';
	import type { IndexerQueryResult } from '$lib/api/api';

	// The cells of one row in the full "all torrents" list; TorrentTable renders the row itself.
	let {
		torrent,
		downloading,
		disabled,
		onDownload
	}: {
		torrent: IndexerQueryResult;
		downloading: boolean;
		disabled: boolean;
		onDownload: () => void;
	} = $props();
</script>

<Table.Cell class="font-medium">
	{#if torrent.comments}
		<a
			href={torrent.comments}
			target="_blank"
			rel="noopener noreferrer external"
			class="hover:underline">{torrent.title}</a
		>
	{:else}
		{torrent.title}
	{/if}
</Table.Cell>
<Table.Cell>{torrent.slot_label ?? '—'}</Table.Cell>
<Table.Cell>{formatSize(torrent.size)}</Table.Cell>
<Table.Cell>{torrent.seeders}</Table.Cell>
<Table.Cell>
	<TorrentScoreValue score={torrent.score} breakdown={torrent.score_breakdown} />
</Table.Cell>
<Table.Cell>{torrent.indexer ?? 'Unknown'}</Table.Cell>
<Table.Cell>
	{#each torrent.flags as flag (flag)}
		<Badge variant="outline">{flag}</Badge>
	{/each}
</Table.Cell>
<Table.Cell class="text-right">
	<Button class="w-full" {disabled} onclick={onDownload}>
		{#if downloading}
			<LoaderCircle class="animate-spin" />
		{:else}
			<Download />
		{/if}
		Download
	</Button>
</Table.Cell>
