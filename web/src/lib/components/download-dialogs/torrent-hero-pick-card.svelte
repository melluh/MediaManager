<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import Captions from '@lucide/svelte/icons/captions';
	import Download from '@lucide/svelte/icons/download';
	import Film from '@lucide/svelte/icons/film';
	import Gauge from '@lucide/svelte/icons/gauge';
	import HardDrive from '@lucide/svelte/icons/hard-drive';
	import Star from '@lucide/svelte/icons/star';
	import Tag from '@lucide/svelte/icons/tag';
	import Users from '@lucide/svelte/icons/users';
	import SelectFilePathSuffixDialog from '$lib/components/download-dialogs/select-file-path-suffix-dialog.svelte';
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
	import type { IndexerQueryResult, Movie, Show } from '$lib/api/api';

	let {
		result,
		slotLabel,
		media,
		filePathSuffix = $bindable(),
		onDownload
	}: {
		result: IndexerQueryResult;
		slotLabel: string;
		media: Movie | Show;
		filePathSuffix: string;
		onDownload: (resultId: string) => void;
	} = $props();

	let subtitleSummary = $derived(formatSubtitles(result.attributes?.subtitles));
	let mbpsText = $derived(formatMbps(result.effective_mbps));
	let seedersText = $derived(formatSeeders(result.usenet, result.seeders));
	let groupText = $derived(formatGroup(result.attributes?.release_group));
	let codecText = $derived(formatCodec(result.attributes?.codec));
	let sizeText = $derived(formatSize(result.size));
</script>

<Card.Root class="flex flex-col border-primary shadow-md">
	<Card.Header class="flex-row items-start justify-between gap-2 space-y-0 pb-2">
		<div class="flex min-w-0 flex-col gap-1">
			<div class="flex items-center gap-2">
				<Card.Title class="text-lg">{slotLabel}</Card.Title>
				<Badge>Top Pick</Badge>
			</div>
			<div class="truncate text-sm text-muted-foreground" title={result.title}>
				{#if result.comments}
					<a
						href={result.comments}
						target="_blank"
						rel="noopener noreferrer external"
						class="hover:underline"
					>
						{result.title}
					</a>
				{:else}
					{result.title}
				{/if}
			</div>
		</div>
		<TorrentIndexerLink indexer={result.indexer} comments={result.comments} />
	</Card.Header>

	<Card.Content class="flex flex-1 flex-col gap-3 pt-2 text-sm">
		<TorrentBadges
			hdrFlags={result.attributes?.hdr_flags}
			freeleech={result.flags.includes('freeleech')}
		/>

		<div class="flex flex-wrap gap-2">
			<TorrentStat icon={HardDrive} label="Size" value={sizeText} />
			<TorrentStat icon={Gauge} label="Bitrate" value={mbpsText} />
			<TorrentStat icon={Users} label="Seeders" value={seedersText} />
			<TorrentStat icon={Tag} label="Group" value={groupText} />
			<TorrentStat icon={Film} label="Codec" value={codecText} />
			<TorrentStat icon={Captions} label="Subtitles" value={subtitleSummary} />
			<TorrentStat icon={Star} label="Score">
				<TorrentScoreValue score={result.score} breakdown={result.score_breakdown} />
			</TorrentStat>
		</div>
	</Card.Content>

	<Card.Footer class="items-center justify-between gap-2">
		<div class="flex-1">
			<SelectFilePathSuffixDialog
				bind:filePathSuffix
				{media}
				callback={() => onDownload(result.id as string)}
				size="lg"
			>
				{#snippet triggerIcon()}
					<Download />
				{/snippet}
			</SelectFilePathSuffixDialog>
		</div>
	</Card.Footer>
</Card.Root>
