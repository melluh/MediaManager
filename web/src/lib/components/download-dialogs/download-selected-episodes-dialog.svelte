<script lang="ts">
	import { Button, buttonVariants } from '$lib/components/ui/button';
	import { toast } from 'svelte-sonner';
	import { formatSecondsToOptimalUnit, getTorrentQualityString } from '$lib/utils';
	import { cn } from '$lib/utils';
	import * as Table from '$lib/components/ui/table';
	import * as Collapsible from '$lib/components/ui/collapsible';
	import { Badge } from '$lib/components/ui/badge';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Download from '@lucide/svelte/icons/download';
	import client from '$lib/api';
	import type { IndexerQueryResult, Show } from '$lib/api/api';
	import SelectFilePathSuffixDialog from '$lib/components/download-dialogs/select-file-path-suffix-dialog.svelte';
	import { invalidateAll } from '$app/navigation';
	import TorrentTable from '$lib/components/download-dialogs/torrent-table.svelte';
	import DownloadDialogWrapper from '$lib/components/download-dialogs/download-dialog-wrapper.svelte';
	import TorrentScoreCell from '$lib/components/download-dialogs/torrent-score-cell.svelte';
	import TorrentPickCard from '$lib/components/download-dialogs/torrent-pick-card.svelte';
	import { groupIntoSlots } from '$lib/components/download-dialogs/torrent-grouping';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';

	let {
		show,
		selectedEpisodeNumbers,
		triggerText = 'Download Episodes'
	}: {
		show: Show;
		selectedEpisodeNumbers: { seasonNumber: number; episodeNumber: number }[];
		triggerText?: string;
	} = $props();

	const dialogueState = shallowDialog('downloadSelectedEpisodes');
	let torrentsPromise: Promise<IndexerQueryResult[]> | undefined = $state();
	let torrentsData: IndexerQueryResult[] | null = $state(null);
	let torrentsError: string | null = $state(null);
	let isLoading: boolean = $state(false);
	let filePathSuffix: string = $state('');
	let showFullList: boolean = $state(false);
	let grouped = $derived(groupIntoSlots(torrentsData));
	let selectedResultId: string | null = $derived(grouped.heroPick?.result.id ?? null);

	const tableColumnHeadings = [
		{ name: 'Quality', id: 'quality' },
		{ name: 'Size', id: 'size' },
		{ name: 'Usenet', id: 'usenet' },
		{ name: 'Seeders', id: 'seeders' },
		{ name: 'Age', id: 'age' },
		{ name: 'Score', id: 'score' },
		{ name: 'Indexer', id: 'indexer' },
		{ name: 'Indexer Flags', id: 'flags' }
	];

	function torrentMatchesSelectedEpisodes(
		torrentTitle: string,
		selectedEpisodes: { seasonNumber: number; episodeNumber: number }[]
	) {
		const normalizedTitle = torrentTitle.toLowerCase();

		return selectedEpisodes.some((ep) => {
			const s = String(ep.seasonNumber).padStart(2, '0');
			const e = String(ep.episodeNumber).padStart(2, '0');

			const patterns = [
				`s${s}e${e}`,
				`${s}x${e}`,
				`season ${ep.seasonNumber} episode ${ep.episodeNumber}`
			];

			return patterns.some((pattern) => normalizedTitle.includes(pattern));
		});
	}

	async function search() {
		if (!selectedEpisodeNumbers || selectedEpisodeNumbers.length === 0) {
			toast.error('No episodes selected.');
			return;
		}

		isLoading = true;
		torrentsError = null;
		torrentsData = null;

		torrentsPromise = Promise.all(
			selectedEpisodeNumbers.map((ep) =>
				client
					.GET('/api/v1/tv/torrents', {
						params: {
							query: {
								show_id: show.id!,
								season_number: ep.seasonNumber,
								episode_number: ep.episodeNumber
							}
						}
					})
					.then((r) => r?.data ?? [])
			)
		)
			.then((results) => results.flat())
			.then((allTorrents) =>
				allTorrents.filter((torrent) =>
					torrentMatchesSelectedEpisodes(torrent.title, selectedEpisodeNumbers)
				)
			)
			.finally(() => (isLoading = false));

		try {
			torrentsData = await torrentsPromise;
		} catch (error) {
			console.error(error);
			torrentsError =
				(error instanceof Error && error.message) ||
				'An error occurred while searching for torrents.';
			toast.error(torrentsError);
		}
	}

	async function downloadTorrent(result_id: string) {
		const { response } = await client.POST('/api/v1/tv/torrents', {
			params: {
				query: {
					show_id: show.id!,
					public_indexer_result_id: result_id,
					override_file_path_suffix: filePathSuffix === '' ? undefined : filePathSuffix
				}
			}
		});

		if (!response.ok) {
			toast.error('Download failed.');
		} else {
			toast.success('Download started.');
		}

		await invalidateAll();
	}
</script>

<DownloadDialogWrapper
	bind:open={() => dialogueState.open, (v) => (dialogueState.open = v)}
	{triggerText}
	triggerClass={cn(
		buttonVariants({ variant: 'default' }),
		'bg-blue-600 text-white hover:bg-blue-700'
	)}
	title="Download Selected Episodes"
	description="Search and download torrents for selected episodes."
>
	{#snippet triggerIcon()}
		<Download />
	{/snippet}
	<div class="flex flex-col gap-3">
		<p class="text-sm text-muted-foreground">
			Selected episodes:
			<strong>
				{selectedEpisodeNumbers.length > 0
					? selectedEpisodeNumbers
							.map(
								(e) =>
									`S${String(e.seasonNumber).padStart(2, '0')}E${String(e.episodeNumber).padStart(2, '0')}`
							)
							.join(', ')
					: 'None'}
			</strong>
		</p>

		<Button
			class="w-fit"
			disabled={isLoading || selectedEpisodeNumbers.length === 0}
			onclick={search}
		>
			Search Torrents
		</Button>
	</div>

	{#if torrentsError}
		<div class="my-2 w-full text-center text-red-500">
			An error occurred: {torrentsError}
		</div>
	{/if}

	{#if torrentsData && grouped.allPicks.length > 0}
		<div class="grid grid-cols-1 gap-3 md:grid-cols-3">
			{#each grouped.allPicks as pick (pick.slotName)}
				<TorrentPickCard
					result={pick.result}
					slotLabel={pick.slotLabel}
					selected={selectedResultId === pick.result.id}
					onSelect={() => (selectedResultId = pick.result.id ?? null)}
				/>
			{/each}
		</div>
	{/if}

	<Collapsible.Root bind:open={showFullList} class="w-full space-y-1">
		<Collapsible.Trigger>
			<div class="flex items-center gap-2">
				<Button class="w-9 p-0" size="sm" variant="ghost">
					<ChevronDown />
					<span class="sr-only">Toggle</span>
				</Button>
				<span class="text-sm font-semibold">
					{showFullList ? 'Hide full list' : 'View full list'}
				</span>
			</div>
		</Collapsible.Trigger>
		<Collapsible.Content class="space-y-1">
			<TorrentTable {torrentsPromise} columns={tableColumnHeadings}>
				{#snippet rowSnippet(torrent)}
					<Table.Cell>
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
					<Table.Cell>{getTorrentQualityString(torrent.quality)}</Table.Cell>
					<Table.Cell>
						{(torrent.size / 1024 / 1024 / 1024).toFixed(2)}GB
					</Table.Cell>
					<Table.Cell>{torrent.usenet}</Table.Cell>
					<Table.Cell>{torrent.usenet ? 'N/A' : torrent.seeders}</Table.Cell>
					<Table.Cell>
						{torrent.age ? formatSecondsToOptimalUnit(torrent.age) : torrent.usenet ? 'N/A' : ''}
					</Table.Cell>
					<TorrentScoreCell score={torrent.score} breakdown={torrent.score_breakdown} />
					<Table.Cell>{torrent.indexer ?? 'unknown'}</Table.Cell>
					<Table.Cell>
						{#if torrent.flags}
							{#each torrent.flags as flag (flag)}
								<Badge variant="outline">{flag}</Badge>
							{/each}
						{/if}
					</Table.Cell>
					<Table.Cell class="text-right">
						<SelectFilePathSuffixDialog
							bind:filePathSuffix
							media={show}
							callback={() => downloadTorrent(torrent.id as string)}
							dialogKey={`downloadSelectedEpisodes:${torrent.id}`}
						/>
					</Table.Cell>
				{/snippet}
			</TorrentTable>
		</Collapsible.Content>
	</Collapsible.Root>
	{#if selectedResultId}
		<div class="flex justify-end pt-2">
			<SelectFilePathSuffixDialog
				bind:filePathSuffix
				media={show}
				callback={() => downloadTorrent(selectedResultId as string)}
				dialogKey="downloadSelectedEpisodes:hero"
				size="lg"
			>
				{#snippet triggerIcon()}
					<Download />
				{/snippet}
			</SelectFilePathSuffixDialog>
		</div>
	{/if}
</DownloadDialogWrapper>
