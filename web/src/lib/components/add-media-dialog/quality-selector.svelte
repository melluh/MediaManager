<script lang="ts">
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import {
		formatTorrentSize,
		qualityOptions,
		type MediaQuality,
		type SelectedTorrents
	} from './types';

	let {
		selectedQuality = $bindable(),
		selectedTorrents
	}: { selectedQuality: MediaQuality | undefined; selectedTorrents?: SelectedTorrents } = $props();
</script>

<ToggleGroup.Root
	type="single"
	bind:value={selectedQuality}
	class="grid grid-cols-2 gap-3 sm:grid-cols-4"
>
	{#each qualityOptions as quality (quality.value)}
		{@const torrent = selectedTorrents?.[quality.value]}
		<ToggleGroup.Item
			value={quality.value}
			disabled={selectedTorrents !== undefined && !torrent}
			class="flex h-auto min-h-24 w-full flex-col items-center justify-center gap-1 rounded-lg border-2 border-border bg-transparent px-2 py-3 text-base font-semibold transition-colors hover:border-muted-foreground/50 data-[state=on]:border-primary data-[state=on]:bg-primary/5 data-[state=on]:text-primary [&_svg]:size-5"
		>
			<quality.icon />
			{quality.label}
			<span class="text-xs font-normal text-muted-foreground">{quality.sublabel}</span>
			{#if torrent}
				<span class="text-[11px] font-normal text-muted-foreground">
					{formatTorrentSize(torrent.size)}
				</span>
			{/if}
		</ToggleGroup.Item>
	{/each}
</ToggleGroup.Root>
