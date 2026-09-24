<script lang="ts">
	import { Button, buttonVariants } from '$lib/components/ui/button';
	import { toast } from 'svelte-sonner';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import CircleAlert from '@lucide/svelte/icons/circle-alert';
	import Download from '@lucide/svelte/icons/download';
	import List from '@lucide/svelte/icons/list';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import SearchX from '@lucide/svelte/icons/search-x';
	import { cn } from '$lib/utils';
	import { untrack } from 'svelte';

	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import client from '$lib/api';
	import type { IndexerQueryResult, Movie } from '$lib/api/api';
	import { invalidateAll } from '$app/navigation';
	import EmptyState from '$lib/components/empty-state.svelte';
	import TorrentTable from '$lib/components/download-dialogs/torrent-table.svelte';
	import TorrentResultRow from '$lib/components/download-dialogs/torrent-result-row.svelte';
	import TorrentPickCarousel from '$lib/components/download-dialogs/torrent-pick-carousel.svelte';
	import DownloadDialogWrapper from '$lib/components/download-dialogs/download-dialog-wrapper.svelte';
	import { groupIntoSlots } from '$lib/components/download-dialogs/torrent-grouping';
	import { formatSize } from '$lib/components/download-dialogs/torrent-format';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';

	let {
		movie,
		hasImportedFile = false,
		asMenuItem = false,
		menuLabel
	}: {
		movie: Movie;
		hasImportedFile?: boolean;
		asMenuItem?: boolean;
		menuLabel?: string;
	} = $props();
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
		{ name: 'Slot', id: 'slot_index' },
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
			const { data, error, response } = await client.POST(`/api/v1/movies/{movie_id}/torrents`, {
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
					'A movie file or pending download for this version already exists. Pick a different release.';
				console.warn(errorMessage);
				torrentsError = errorMessage;
				if (dialogueState.open) toast.info(errorMessage);
			} else if (!response.ok) {
				const errorMessage =
					(error as { detail?: string } | undefined)?.detail ??
					`Failed to download torrent for movie ${movie.id}: ${response.statusText}`;
				console.error(errorMessage);
				torrentsError = errorMessage;
				toast.error(errorMessage);
			} else {
				console.log('Downloading torrent:', data);
				toast.success('Torrent download started successfully!');
			}
			// Refresh before closing: closing the dialog pops a shallow-routed
			// history entry (see shallowDialog's own warning about racing async
			// work against that history.back()) - invalidating first ensures the
			// movie's new "Downloading" state is already loaded by the time the
			// dialog closes, instead of racing the history navigation and losing.
			await invalidateAll();
			if (response.ok) {
				dialogueState.open = false;
			}
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
			.then(({ data, error }) => {
				if (error) {
					torrentsError =
						(error as { detail?: string } | undefined)?.detail ?? 'Failed to search for torrents.';
					return undefined;
				}
				return data;
			})
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
	bind:open={dialogueState.open}
	triggerText="Download"
	triggerClass={hasImportedFile
		? buttonVariants({ variant: 'secondary' })
		: cn(buttonVariants({ variant: 'default' }), 'bg-blue-600 text-white hover:bg-blue-700')}
	{asMenuItem}
	{menuLabel}
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
				<TorrentResultRow
					{torrent}
					downloading={downloadingResultId === torrent.id}
					disabled={downloadingResultId !== null}
					onDownload={() => downloadTorrent(torrent.id as string)}
				/>
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
			<EmptyState icon={CircleAlert} title="An error occurred" destructive class="my-2">
				{torrentsError}
			</EmptyState>
		{:else if !isLoading && torrentsData && grouped.allPicks.length === 0}
			<EmptyState icon={SearchX} title="No torrents found" class="my-2">
				Try a different search query.
			</EmptyState>
		{/if}
		{#if isLoading || (torrentsData && grouped.allPicks.length > 0)}
			<TorrentPickCarousel
				picks={grouped.allPicks}
				loading={isLoading}
				{selectedResultId}
				onSelect={(id) => (selectedResultId = id)}
			/>
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
					{#if downloadingResultId !== null && downloadingResultId === selectedResultId}
						<LoaderCircle class="animate-spin" />
					{:else}
						<Download />
					{/if}
					{selectedResult ? `Download (${formatSize(selectedResult.size)})` : 'Download'}
				</Button>
			</div>
		{:else if torrentsData}
			<div class="flex justify-end pt-2">
				<Button variant="secondary" size="sm" onclick={() => (showFullList = true)}>
					<List />
					View all torrents
				</Button>
			</div>
		{/if}
	{/if}
</DownloadDialogWrapper>
