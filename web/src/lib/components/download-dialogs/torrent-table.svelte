<script lang="ts">
	import { ArrowDown, ArrowUp, LoaderCircle } from 'lucide-svelte';
	import * as Table from '$lib/components/ui/table';
	import { type Snippet } from 'svelte';
	import type { IndexerQueryResult } from '$lib/api/api';

	let {
		torrentsPromise,
		columns,
		rowSnippet
	}: {
		torrentsPromise: Promise<IndexerQueryResult[] | undefined> | null | undefined;
		columns: { name: string; id: string }[];
		rowSnippet: Snippet<[IndexerQueryResult]>;
	} = $props();

	// Defaults to slot_index (the backend's slot-priority-then-score order):
	// `score` is only ever comparable within a single slot, so sorting this
	// raw/full list by score by default would visually scramble tiers.
	let sortBy = $state({ col: 'slot_index', ascending: true });

	function getSortedColumnState(column: string | undefined): boolean | null {
		if (sortBy.col !== column) return null;
		return sortBy.ascending;
	}

	function toggleSort(column: string) {
		if (column === sortBy.col) {
			sortBy.ascending = !sortBy.ascending;
		} else {
			sortBy = { col: column, ascending: true };
		}
	}
	function compareValues(a: unknown, b: unknown): number {
		if (typeof a === 'number' && typeof b === 'number') return a - b;
		if (typeof a === 'boolean' && typeof b === 'boolean') return Number(a) - Number(b);
		return String(a).localeCompare(String(b));
	}

	function sort(
		data: IndexerQueryResult[],
		column: string,
		ascending: boolean
	): IndexerQueryResult[] {
		let modifier = ascending ? 1 : -1;
		return [...data].sort((a, b) => {
			const aVal = (a as Record<string, unknown>)[column];
			const bVal = (b as Record<string, unknown>)[column];
			// Unslotted results (slot_index == null) always sort last,
			// regardless of direction - they never belong ahead of a
			// classified pick.
			if (column === 'slot_index') {
				if (aVal == null && bVal == null) return 0;
				if (aVal == null) return 1;
				if (bVal == null) return -1;
			}
			return compareValues(aVal, bVal) * modifier;
		});
	}
</script>

<div class="items-center">
	{#await torrentsPromise}
		<div class="flex w-full max-w-sm items-center space-x-2">
			<LoaderCircle class="animate-spin" />
			<p>Loading torrents...</p>
		</div>
	{:then data}
		<div class="overflow-y-auto rounded-md border p-2">
			<Table.Root>
				<Table.Header>
					<Table.Row>
						<Table.Head>Title</Table.Head>
						{#each columns as column (column.id)}
							<Table.Head onclick={() => toggleSort(column.id)} class="cursor-pointer">
								<div class="inline-flex items-center">
									{column.name}
									{#if getSortedColumnState(column.id) === true}
										<ArrowUp />
									{:else if getSortedColumnState(column.id) === false}
										<ArrowDown />
									{:else}
										<!-- Preserve layout (column width) when no sort is applied -->
										<ArrowUp class="invisible"></ArrowUp>
									{/if}
								</div>
							</Table.Head>
						{/each}
						<Table.Head class="text-right">Actions</Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#if data}
						{@const sortedData = sort(data, sortBy.col, sortBy.ascending)}
						{#each sortedData as torrent (torrent.id)}
							<Table.Row>
								{@render rowSnippet(torrent)}
							</Table.Row>
						{:else}
							<Table.Cell colspan={columns.length + 2}>
								<div class="font-light text-center w-full">No torrents found.</div>
							</Table.Cell>
						{/each}
					{:else}
						<Table.Cell colspan={columns.length + 2}>
							<div class="w-full text-center font-light">
								Start searching by clicking the search button!
							</div>
						</Table.Cell>
					{/if}
				</Table.Body>
			</Table.Root>
		</div>
	{:catch error}
		<div class="w-full text-center text-red-500">Failed to load torrents.</div>
		<div class="w-full text-center text-red-500">Error: {error.message}</div>
	{/await}
</div>
