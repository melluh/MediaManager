<script lang="ts">
	import { Button, buttonVariants } from '$lib/components/ui/button';
	import { toast } from 'svelte-sonner';
	import { Badge } from '$lib/components/ui/badge';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Download from '@lucide/svelte/icons/download';
	import List from '@lucide/svelte/icons/list';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import { cn } from '$lib/utils';
	import { untrack } from 'svelte';

	import * as Table from '$lib/components/ui/table';
	import * as Carousel from '$lib/components/ui/carousel';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import client from '$lib/api';
	import type { IndexerQueryResult, Movie } from '$lib/api/api';
	import { invalidateAll } from '$app/navigation';
	import TorrentTable from '$lib/components/download-dialogs/torrent-table.svelte';
	import DownloadDialogWrapper from '$lib/components/download-dialogs/download-dialog-wrapper.svelte';
	import TorrentScoreCell from '$lib/components/download-dialogs/torrent-score-cell.svelte';
	import TorrentPickCard from '$lib/components/download-dialogs/torrent-pick-card.svelte';
	import { groupIntoSlots } from '$lib/components/download-dialogs/torrent-grouping';
	import { formatSize } from '$lib/components/download-dialogs/torrent-format';
	import { getTorrentQualityString } from '$lib/utils';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';

	let { movie, hasImportedFile = false }: { movie: Movie; hasImportedFile?: boolean } = $props();
	const dialogueState = shallowDialog('downloadMovie');
	let torrentsError: string | null = $state(null);
	let queryOverride: string = $state('');

	let torrentsPromise: Promise<IndexerQueryResult[] | undefined> | null = $state(null);
	let torrentsData: IndexerQueryResult[] | null = $state(null);
	let isLoading: boolean = $state(false);
	let downloadingResultId: string | null = $state(null);
	let showFullList: boolean = $state(false);
	let customSearchOpen: boolean = $state(false);
	let grouped = $derived(groupIntoSlots(torrentsData));
	let selectedResultId: string | null = $derived(grouped.heroPick?.result.id ?? null);
	let selectedResult = $derived(
		grouped.allPicks.find((pick) => pick.result.id === selectedResultId)?.result
	);

	const tableColumnHeadings = [
		{ name: 'Quality', id: 'quality' },
		{ name: 'Size', id: 'size' },
		{ name: 'Seeders', id: 'seeders' },
		{ name: 'Score', id: 'score' },
		{ name: 'Indexer', id: 'indexer' },
		{ name: 'Indexer Flags', id: 'flags' }
	];

	async function downloadTorrent(result_id: string) {
		torrentsError = null;
		downloadingResultId = result_id;
		try {
			const { data, response } = await client.POST(`/api/v1/movies/{movie_id}/torrents`, {
				params: {
					path: {
						movie_id: movie.id!
					},
					query: {
						public_indexer_result_id: result_id
					}
				}
			});
			if (response.status === 409) {
				const errorMessage =
					'A movie file for this quality/version already exists. Pick a different release.';
				console.warn(errorMessage);
				torrentsError = errorMessage;
				if (dialogueState.open) toast.info(errorMessage);
			} else if (!response.ok) {
				const errorMessage = `Failed to download torrent for movie ${movie.id}: ${response.statusText}`;
				console.error(errorMessage);
				torrentsError = errorMessage;
				toast.error(errorMessage);
			} else {
				console.log('Downloading torrent:', data);
				toast.success('Torrent download started successfully!');
				dialogueState.open = false;
			}
			await invalidateAll();
		} finally {
			downloadingResultId = null;
		}
	}

	async function search() {
		isLoading = true;
		torrentsError = null;
		torrentsData = null;
		torrentsPromise = client
			.GET('/api/v1/movies/{movie_id}/torrents', {
				params: {
					query: {
						search_query_override:
							customSearchOpen && queryOverride !== '' ? queryOverride : undefined
					},
					path: {
						movie_id: movie.id!
					}
				}
			})
			.then((data) => data?.data)
			.finally(() => (isLoading = false));
		torrentsData = (await torrentsPromise) ?? null;
	}

	// TODO: reimplement
	// function searchAgain() {
	// 	customSearchOpen = false;
	// 	queryOverride = '';
	// 	search();
	// }

	// function openCustomSearch() {
	// 	customSearchOpen = true;
	// }

	$effect(() => {
		if (dialogueState.open) {
			untrack(() => {
				customSearchOpen = false;
				queryOverride = '';
				search();
			});
		}
	});
</script>

<DownloadDialogWrapper
	bind:open={() => dialogueState.open, (v) => (dialogueState.open = v)}
	triggerText="Download Movie"
	triggerClass={hasImportedFile
		? buttonVariants({ variant: 'secondary' })
		: cn(buttonVariants({ variant: 'default' }), 'bg-blue-600 text-white hover:bg-blue-700')}
	title={`Download ${movie.name}`}
>
	{#snippet triggerIcon()}
		<Download />
	{/snippet}
	{#if showFullList}
		<Button variant="ghost" size="sm" class="w-fit" onclick={() => (showFullList = false)}>
			<ArrowLeft />
			Back
		</Button>
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
				<Table.Cell>{torrent.seeders}</Table.Cell>
				<TorrentScoreCell score={torrent.score} breakdown={torrent.score_breakdown} />
				<Table.Cell>{torrent.indexer ?? 'Unknown'}</Table.Cell>
				<Table.Cell>
					{#each torrent.flags as flag (flag)}
						<Badge variant="outline">{flag}</Badge>
					{/each}
				</Table.Cell>
				<Table.Cell class="text-right">
					<Button
						class="w-full"
						disabled={downloadingResultId !== null}
						onclick={() => downloadTorrent(torrent.id as string)}
					>
						{#if downloadingResultId === torrent.id}
							<LoaderCircle class="animate-spin" />
						{:else}
							<Download />
						{/if}
						Download
					</Button>
				</Table.Cell>
			{/snippet}
		</TorrentTable>
	{:else}
		{#if customSearchOpen}
			<div class="grid w-full items-center gap-1.5">
				<Label for="query-override">Enter a custom query</Label>
				<div class="flex w-full max-w-sm items-center space-x-2">
					<Input bind:value={queryOverride} id="query-override" type="text" />
					<Button disabled={isLoading} class="w-fit" onclick={search}>Search</Button>
				</div>
				<p class="text-sm text-muted-foreground">
					The custom query will override the default search string like 'A Minecraft Movie (2025)'.
				</p>
			</div>
		{/if}
		{#if torrentsError}
			<div class="my-2 w-full text-center text-red-500">An error occurred: {torrentsError}</div>
		{/if}
		{#if isLoading || (torrentsData && grouped.allPicks.length > 0)}
			<Carousel.Root class="mx-8 my-4 min-w-0">
				<Carousel.Content>
					{#if isLoading}
						{#each { length: 3 }}
							<Carousel.Item class="basis-full sm:basis-1/2 lg:basis-1/3">
								<Skeleton class="h-95 w-full rounded-lg" />
							</Carousel.Item>
						{/each}
					{:else}
						{#each grouped.allPicks as pick (pick.slotName)}
							<Carousel.Item class="basis-full sm:basis-1/2 lg:basis-1/3">
								<TorrentPickCard
									result={pick.result}
									slotLabel={pick.slotLabel}
									selected={selectedResultId === pick.result.id}
									onSelect={() => (selectedResultId = pick.result.id ?? null)}
								/>
							</Carousel.Item>
						{/each}
					{/if}
				</Carousel.Content>
				<Carousel.Previous />
				<Carousel.Next />
				{#if isLoading}
					<div
						class="absolute inset-0 flex flex-col items-center justify-center gap-2 rounded-lg bg-background/70 backdrop-blur-sm"
					>
						<LoaderCircle class="size-6 animate-spin text-muted-foreground" />
						<span class="text-sm text-muted-foreground">Searching for torrents...</span>
					</div>
				{/if}
			</Carousel.Root>
		{/if}
		{#if torrentsData || isLoading}
			<div class="flex items-center justify-between gap-2 pt-2">
				<Button
					variant="secondary"
					size="sm"
					disabled={isLoading || downloadingResultId !== null}
					onclick={() => (showFullList = true)}
				>
					<List />
					View all torrents
				</Button>
				<Button
					size="lg"
					disabled={isLoading || !selectedResultId || downloadingResultId !== null}
					onclick={() => downloadTorrent(selectedResultId as string)}
				>
					{#if downloadingResultId === selectedResultId}
						<LoaderCircle class="animate-spin" />
					{:else}
						<Download />
					{/if}
					{selectedResult ? `Download (${formatSize(selectedResult.size)})` : 'Download'}
				</Button>
			</div>
		{/if}
	{/if}
</DownloadDialogWrapper>
