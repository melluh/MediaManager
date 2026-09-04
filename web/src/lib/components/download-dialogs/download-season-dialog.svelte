<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { toast } from 'svelte-sonner';
	import {
		convertTorrentSeasonRangeToIntegerRange,
		formatSecondsToOptimalUnit,
		getTorrentQualityString
	} from '$lib/utils.ts';
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
	import SearchTabs from '$lib/components/download-dialogs/search-tabs.svelte';
	import DownloadDialogWrapper from '$lib/components/download-dialogs/download-dialog-wrapper.svelte';
	import TorrentScoreCell from '$lib/components/download-dialogs/torrent-score-cell.svelte';
	import TorrentPickCard from '$lib/components/download-dialogs/torrent-pick-card.svelte';
	import { groupIntoSlots } from '$lib/components/download-dialogs/torrent-grouping';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';

	let { show }: { show: Show } = $props();
	const dialogueState = shallowDialog('downloadSeason');
	let selectedSeasonNumber: number = $state(1);
	let torrentsError: string | null = $state(null);
	let queryOverride: string = $state('');
	let filePathSuffix: string = $state('');

	let torrentsPromise: Promise<IndexerQueryResult[] | undefined> | undefined = $state();
	let torrentsData: IndexerQueryResult[] | null = $state(null);
	let tabState: string = $state('basic');
	let isLoading: boolean = $state(false);
	let showFullList: boolean = $state(false);
	let grouped = $derived(groupIntoSlots(torrentsData));
	let selectedResultId: string | null = $derived(grouped.heroPick?.result.id ?? null);

	let advancedMode: boolean = $derived(tabState === 'advanced');

	const tableColumnHeadings = [
		{ name: 'Quality', id: 'quality' },
		{ name: 'Size', id: 'size' },
		{ name: 'Usenet', id: 'usenet' },
		{ name: 'Seeders', id: 'seeders' },
		{ name: 'Age', id: 'age' },
		{ name: 'Score', id: 'score' },
		{ name: 'Indexer', id: 'indexer' },
		{ name: 'Indexer Flags', id: 'flags' },
		{ name: 'Seasons', id: 'season' }
	];

	async function downloadTorrent(result_id: string) {
		torrentsError = null;
		const { error, response } = await client.POST('/api/v1/tv/torrents', {
			params: {
				query: {
					show_id: show.id!,
					public_indexer_result_id: result_id,
					override_file_path_suffix: filePathSuffix === '' ? undefined : filePathSuffix
				}
			}
		});
		if (response.status === 409) {
			const errorMessage = `There already is a Season File using the Filepath Suffix '${filePathSuffix}'. Try again with a different Filepath Suffix.`;
			console.warn(errorMessage);
			torrentsError = errorMessage;
			if (dialogueState.open) toast.info(errorMessage);
		} else if (!response.ok) {
			const errorMessage =
				(error as { detail?: string } | undefined)?.detail ??
				`Failed to download torrent for show ${show.id} and season ${selectedSeasonNumber}: ${response.statusText}`;
			console.error(errorMessage);
			torrentsError = errorMessage;
			toast.error(errorMessage);
		} else {
			toast.success('Torrent download started successfully!');
		}
		await invalidateAll();
	}

	async function search() {
		isLoading = true;
		torrentsError = null;
		torrentsData = null;
		torrentsPromise = client
			.GET('/api/v1/tv/torrents', {
				params: {
					query: {
						show_id: show.id!,
						search_query_override: advancedMode ? queryOverride : undefined,
						season_number: advancedMode ? undefined : selectedSeasonNumber
					}
				}
			})
			.then(({ data, error }) => {
				if (error) {
					torrentsError =
						(error as { detail?: string } | undefined)?.detail ?? 'Failed to search for torrents.';
					return undefined;
				}
				return data;
			})
			.finally(() => (isLoading = false));

		toast.info('Searching for torrents...');

		torrentsData = (await torrentsPromise) ?? null;
		if (!torrentsError) toast.info('Found ' + torrentsData?.length + ' torrents.');
	}
</script>

<DownloadDialogWrapper
	bind:open={() => dialogueState.open, (v) => (dialogueState.open = v)}
	triggerText="Download Seasons"
	title="Download a Season"
	description="Search and download torrents for a specific season or season packs."
>
	<SearchTabs
		bind:tabState
		{isLoading}
		bind:queryOverride
		onSearch={search}
		advancedModeHelpText="The custom query will override the default search string like 'The Simpsons Season 3'. Note that only Seasons which are listed in the 'Seasons' cell will be imported!"
	>
		{#snippet basicModeContent()}
			<Label for="season-number">
				Enter a season number from 1 to {show.seasons.at(-1)?.number}
			</Label>
			<div class="flex w-full max-w-sm items-center space-x-2">
				<Input
					type="number"
					id="season-number"
					bind:value={selectedSeasonNumber}
					max={show.seasons.at(-1)?.number}
				/>
				<Button disabled={isLoading} class="w-fit" onclick={search}>Search for Torrents</Button>
			</div>
			<p class="text-sm text-muted-foreground">
				Enter the season's number you want to search for. The first, usually 1, or the last season
				number usually yield the most season packs. Note that only Seasons which are listed in the
				"Seasons" cell will be imported!
			</p>
		{/snippet}
	</SearchTabs>
	{#if torrentsError}
		<div class="my-2 w-full text-center text-red-500">An error occurred: {torrentsError}</div>
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
					<Table.Cell>{getTorrentQualityString(torrent.quality)}</Table.Cell>
					<Table.Cell>{(torrent.size / 1024 / 1024 / 1024).toFixed(2)}GB</Table.Cell>
					<Table.Cell>{torrent.usenet}</Table.Cell>
					<Table.Cell>{torrent.usenet ? 'N/A' : torrent.seeders}</Table.Cell>
					<Table.Cell
						>{torrent.age
							? formatSecondsToOptimalUnit(torrent.age)
							: torrent.usenet
								? 'N/A'
								: ''}</Table.Cell
					>
					<TorrentScoreCell score={torrent.score} breakdown={torrent.score_breakdown} />
					<Table.Cell>{torrent.indexer ?? 'unknown'}</Table.Cell>
					<Table.Cell>
						{#if torrent.flags}
							{#each torrent.flags as flag (flag)}
								<Badge variant="outline">{flag}</Badge>
							{/each}
						{/if}
					</Table.Cell>
					<Table.Cell>
						{#if torrent.season}
							{convertTorrentSeasonRangeToIntegerRange(torrent.season)}
						{/if}
					</Table.Cell>
					<Table.Cell class="text-right">
						<SelectFilePathSuffixDialog
							bind:filePathSuffix
							media={show}
							callback={() => downloadTorrent(torrent.id as string)}
							dialogKey={`downloadSeason:${torrent.id}`}
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
				dialogKey="downloadSeason:hero"
				size="lg"
			>
				{#snippet triggerIcon()}
					<Download />
				{/snippet}
			</SelectFilePathSuffixDialog>
		</div>
	{/if}
</DownloadDialogWrapper>
