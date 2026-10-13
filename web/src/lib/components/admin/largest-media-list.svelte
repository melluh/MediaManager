<script lang="ts">
	import { resolve } from '$app/paths';
	import Clapperboard from '@lucide/svelte/icons/clapperboard';
	import TvIcon from '@lucide/svelte/icons/tv';
	import Layers from '@lucide/svelte/icons/layers';
	import * as Select from '$lib/components/ui/select/index.js';
	import type { LargestMediaItem } from '$lib/api/api';
	import { formatBytes } from '$lib/utils';

	let { items, class: className }: { items: LargestMediaItem[]; class?: string } = $props();

	// The backend sends up to this many of each type, so every filter can fill it.
	const LIMIT = 20;

	type Filter = 'all' | LargestMediaItem['media_type'];
	const filterOptions: Record<Filter, { label: string; icon: typeof Layers }> = {
		all: { label: 'All', icon: Layers },
		movie: { label: 'Movies', icon: Clapperboard },
		show: { label: 'TV Shows', icon: TvIcon }
	};

	let filter = $state<Filter>('all');
	let selected = $derived(filterOptions[filter]);
	let shown = $derived(
		items.filter((item) => filter === 'all' || item.media_type === filter).slice(0, LIMIT)
	);

	const linkClass = 'flex items-center justify-between gap-2 py-2 hover:underline';
</script>

{#snippet row(item: LargestMediaItem)}
	<span class="flex min-w-0 items-center gap-2">
		{#if item.media_type === 'show'}
			<TvIcon class="size-4 shrink-0 text-muted-foreground" aria-label="TV Show" />
		{:else}
			<Clapperboard class="size-4 shrink-0 text-muted-foreground" aria-label="Movie" />
		{/if}
		<span class="truncate">
			<span class="font-medium">{item.name}</span>
			{#if item.year}
				<span class="text-muted-foreground">({item.year})</span>
			{/if}
		</span>
	</span>
	<span class="shrink-0 text-sm text-muted-foreground">{formatBytes(item.bytes)}</span>
{/snippet}

<section class={className}>
	<div class="mb-2 flex items-center justify-between gap-2">
		<h2 class="text-lg font-semibold">Largest media</h2>
		<Select.Root type="single" bind:value={filter}>
			<Select.Trigger class="w-36 gap-2">
				<!-- A div, since the trigger line-clamps (and so un-flexes) span children. -->
				<div class="flex items-center gap-2">
					<selected.icon class="size-4 text-muted-foreground" />
					{selected.label}
				</div>
			</Select.Trigger>
			<Select.Content>
				<Select.Group>
					{#each Object.entries(filterOptions) as [value, option] (value)}
						<Select.Item {value} label={option.label} class="gap-2">
							<option.icon class="size-4 text-muted-foreground" />
							{option.label}
						</Select.Item>
					{/each}
				</Select.Group>
			</Select.Content>
		</Select.Root>
	</div>
	{#if shown.length === 0}
		<p class="text-sm text-muted-foreground">Nothing found.</p>
	{:else}
		<ol class="flex flex-col divide-y">
			{#each shown as item (item.id)}
				<li>
					{#if item.media_type === 'show'}
						<a href={resolve('/dashboard/tv/[showId]', { showId: item.slug })} class={linkClass}>
							{@render row(item)}
						</a>
					{:else}
						<a
							href={resolve('/dashboard/movies/[movieId]', { movieId: item.slug })}
							class={linkClass}
						>
							{@render row(item)}
						</a>
					{/if}
				</li>
			{/each}
		</ol>
	{/if}
</section>
