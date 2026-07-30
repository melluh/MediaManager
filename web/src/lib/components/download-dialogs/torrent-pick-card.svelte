<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import {
		Captions,
		Circle,
		CircleCheck,
		Film,
		Gauge,
		HardDrive,
		Star,
		Tag,
		Users
	} from 'lucide-svelte';
	import TorrentStat from '$lib/components/download-dialogs/torrent-stat.svelte';
	import TorrentBadges from '$lib/components/download-dialogs/torrent-badges.svelte';
	import TorrentIndexerLink from '$lib/components/download-dialogs/torrent-indexer-link.svelte';
	import TorrentScoreValue from '$lib/components/download-dialogs/torrent-score-value.svelte';
	import {
		formatCodec,
		formatGroup,
		formatMbps,
		formatSeeders,
		formatSize,
		formatSubtitles
	} from '$lib/components/download-dialogs/torrent-format';
	import { cn } from '$lib/utils';
	import type { IndexerQueryResult } from '$lib/api/api';

	let {
		result,
		slotLabel,
		selected,
		onSelect
	}: {
		result: IndexerQueryResult;
		slotLabel: string;
		selected: boolean;
		onSelect: () => void;
	} = $props();

	let subtitleSummary = $derived(formatSubtitles(result.attributes?.subtitles));
	let mbpsText = $derived(formatMbps(result.effective_mbps));
	let seedersText = $derived(formatSeeders(result.usenet, result.seeders));
	let groupText = $derived(formatGroup(result.attributes?.release_group));
	let codecText = $derived(formatCodec(result.attributes?.codec));
	let sizeText = $derived(formatSize(result.size));
</script>

<Card.Root class={cn('flex flex-col', selected && 'border-primary shadow-md')}>
	<Card.Header class="flex-row items-start justify-between gap-2 space-y-0 pb-2">
		<div class="flex min-w-0 flex-col gap-1">
			<div class="flex items-center gap-2">
				<Card.Title class="text-base">{slotLabel}</Card.Title>
			</div>
			<div class="truncate text-xs text-muted-foreground" title={result.title}>
				{result.title}
			</div>
		</div>
		<TorrentIndexerLink indexer={result.indexer} comments={result.comments} />
	</Card.Header>
	<Card.Content class="flex flex-1 flex-col gap-2 pt-2 text-sm">
		<TorrentBadges
			hdrFlags={result.attributes?.hdr_flags}
			freeleech={result.flags.includes('freeleech')}
		/>

		<div class="grid grid-cols-2 gap-2">
			<TorrentStat icon={HardDrive} label="Size" value={sizeText} />
			<TorrentStat icon={Users} label="Seeders" value={seedersText} />
			<TorrentStat icon={Gauge} label="Bitrate" value={mbpsText} />
			<TorrentStat icon={Film} label="Codec" value={codecText} />
			<TorrentStat icon={Captions} label="Subtitles" value={subtitleSummary} />
			<TorrentStat icon={Tag} label="Group" value={groupText} />
			<!-- <TorrentStat icon={Star} label="Score">
				<TorrentScoreValue score={result.score} breakdown={result.score_breakdown} />
			</TorrentStat> -->
		</div>
	</Card.Content>
	<Card.Footer class="items-center gap-2">
		<Button variant={selected ? 'default' : 'outline'} class="w-full" onclick={onSelect}>
			{#if selected}
				<CircleCheck />
				Selected
			{:else}
				<Circle />
				Select
			{/if}
		</Button>
	</Card.Footer>
</Card.Root>
