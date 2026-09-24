<script lang="ts">
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Badge } from '$lib/components/ui/badge';
	import * as Table from '$lib/components/ui/table';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import Check from '@lucide/svelte/icons/check';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import Captions from '@lucide/svelte/icons/captions';
	import Film from '@lucide/svelte/icons/film';
	import Gauge from '@lucide/svelte/icons/gauge';
	import HardDrive from '@lucide/svelte/icons/hard-drive';
	import Tag from '@lucide/svelte/icons/tag';
	import Users from '@lucide/svelte/icons/users';
	import TorrentScoreValue from '$lib/components/download-dialogs/torrent-score-value.svelte';
	import TorrentIndexerLink from '$lib/components/download-dialogs/torrent-indexer-link.svelte';
	import {
		formatCodec,
		formatGroup,
		formatMbps,
		formatSeeders,
		formatSize,
		formatSubtitles
	} from '$lib/components/download-dialogs/torrent-format';
	import {
		pickLabel,
		sortPicks,
		type PickStatus,
		type PlanSlot
	} from '$lib/components/download-dialogs/season-plan';

	let {
		planSlot,
		accepted,
		pickStatus,
		pickErrorMessage,
		disabled,
		onToggle
	}: {
		planSlot: PlanSlot;
		/** Result ids of the picks that will be downloaded. */
		accepted: Set<string>;
		pickStatus: Record<string, PickStatus>;
		pickErrorMessage: Record<string, string>;
		disabled: boolean;
		onToggle: (resultId: string) => void;
	} = $props();

	const columns = [
		{ label: 'Size', icon: HardDrive },
		{ label: 'Seeders', icon: Users },
		{ label: 'Bitrate', icon: Gauge },
		{ label: 'Codec', icon: Film },
		{ label: 'Subtitles', icon: Captions },
		{ label: 'Group', icon: Tag }
	];
</script>

<div class="max-h-[42vh] overflow-y-auto rounded-md border">
	<Table.Root>
		<Table.Header class="sticky top-0 z-10 bg-background">
			<Table.Row>
				<Table.Head class="w-10"></Table.Head>
				<Table.Head>Torrent</Table.Head>
				{#each columns as column (column.label)}
					<Table.Head>
						<div class="flex items-center gap-1">
							<column.icon class="size-3.5" />
							{column.label}
						</div>
					</Table.Head>
				{/each}
				<Table.Head>Score</Table.Head>
				<Table.Head class="w-8"></Table.Head>
			</Table.Row>
		</Table.Header>
		<Table.Body>
			{#each sortPicks(planSlot.picks) as pick (pick.result.id)}
				{@const id = pick.result.id as string}
				{@const status = pickStatus[id]}
				<Table.Row>
					<Table.Cell>
						<Checkbox
							checked={accepted.has(id)}
							disabled={disabled || !!status}
							onCheckedChange={() => onToggle(id)}
						/>
					</Table.Cell>
					<Table.Cell class="max-w-64">
						<div class="flex flex-col gap-0.5">
							<div class="flex flex-wrap items-center gap-1.5">
								<span class="font-medium">{pickLabel(pick)}</span>
								<span class="text-muted-foreground">&middot;</span>
								<TorrentIndexerLink indexer={pick.result.indexer} comments={pick.result.comments} />
								{#if pick.already_downloaded}
									<Badge variant="outline" class="text-xs">Already downloaded</Badge>
								{/if}
							</div>
							<div class="flex min-w-0 items-center gap-1">
								<span
									class="min-w-0 truncate text-xs text-muted-foreground"
									title={pick.result.title}
								>
									{pick.result.title}
								</span>
								{#if pick.result.flags.includes('freeleech')}
									<Badge variant="outline" class="shrink-0 px-1 py-0 text-[10px] text-green-500">
										Freeleech
									</Badge>
								{/if}
							</div>
							{#if status === 'failed'}
								<span class="text-xs text-red-500">{pickErrorMessage[id]}</span>
							{/if}
						</div>
					</Table.Cell>
					<Table.Cell class="whitespace-nowrap">{formatSize(pick.result.size)}</Table.Cell>
					<Table.Cell class="whitespace-nowrap">
						{formatSeeders(pick.result.usenet, pick.result.seeders)}
					</Table.Cell>
					<Table.Cell class="whitespace-nowrap">{formatMbps(pick.result.effective_mbps)}</Table.Cell
					>
					<Table.Cell class="whitespace-nowrap">
						{formatCodec(pick.result.attributes?.codec)}
					</Table.Cell>
					<Table.Cell class="whitespace-nowrap">
						{formatSubtitles(pick.result.attributes?.subtitles)}
					</Table.Cell>
					<Table.Cell class="whitespace-nowrap">
						{formatGroup(pick.result.attributes?.release_group)}
					</Table.Cell>
					<Table.Cell class="whitespace-nowrap">
						<TorrentScoreValue score={pick.result.score} breakdown={pick.result.score_breakdown} />
					</Table.Cell>
					<Table.Cell>
						{#if status === 'starting'}
							<LoaderCircle class="size-4 animate-spin" />
						{:else if status === 'started'}
							<Check class="size-4 stroke-green-500" />
						{:else if status === 'failed'}
							<CircleX class="size-4 stroke-rose-600" />
						{/if}
					</Table.Cell>
				</Table.Row>
			{/each}
		</Table.Body>
	</Table.Root>
</div>
