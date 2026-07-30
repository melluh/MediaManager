<script lang="ts">
	import * as Table from '$lib/components/ui/table';
	import TorrentScoreValue from '$lib/components/download-dialogs/torrent-score-value.svelte';
	import type { ScoreBreakdownEntry } from '$lib/api/api';

	let {
		score,
		breakdown
	}: {
		score: number;
		breakdown?: ScoreBreakdownEntry[];
	} = $props();
</script>

<Table.Cell>
	<TorrentScoreValue {score} {breakdown} />
</Table.Cell>
