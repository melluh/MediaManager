<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import { SvelteSet } from 'svelte/reactivity';
	import type { PublicShow } from '$lib/api/api';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { cn } from '$lib/utils';

	let {
		show,
		selectedSeasonIds = $bindable(),
		error = null,
		onProceed
	}: {
		show: PublicShow;
		selectedSeasonIds: Set<string>;
		error?: string | null;
		onProceed: () => void;
	} = $props();

	function toggleSeason(seasonId: string) {
		if (selectedSeasonIds.has(seasonId)) {
			selectedSeasonIds.delete(seasonId);
		} else {
			selectedSeasonIds.add(seasonId);
		}
		selectedSeasonIds = new SvelteSet(selectedSeasonIds);
	}

	function episodeProgressClass(downloaded: number, total: number) {
		if (total > 0 && downloaded >= total)
			return 'border-transparent bg-green-600 text-white hover:bg-green-600';
		if (downloaded > 0) return 'border-transparent bg-orange-500 text-white hover:bg-orange-500';
		return 'border-transparent bg-muted text-muted-foreground';
	}
</script>

<div class="flex flex-col gap-3">
	<div class="max-h-[50vh] overflow-y-auto rounded-md border">
		{#each show.seasons as season (season.id)}
			{@const total = season.episodes.length}
			{@const downloaded = season.episodes.filter((e) => e.downloaded).length}
			<label
				class="flex cursor-pointer items-center gap-3 border-b px-3 py-2 last:border-b-0 hover:bg-muted/50"
			>
				<Checkbox
					checked={selectedSeasonIds.has(season.id)}
					onCheckedChange={() => toggleSeason(season.id)}
				/>
				<span class="w-14 shrink-0 font-medium">
					S{String(season.number).padStart(2, '0')}
				</span>
				<span class="flex-1 truncate">{season.name}</span>
				<Badge class={cn('shrink-0 tabular-nums', episodeProgressClass(downloaded, total))}>
					{downloaded}/{total}
				</Badge>
			</label>
		{/each}
	</div>
	{#if error}
		<p class="text-sm text-red-500">{error}</p>
	{/if}
	<Button class="w-fit self-end" disabled={selectedSeasonIds.size === 0} onclick={onProceed}>
		Select Torrents
		<ArrowRight />
	</Button>
</div>
