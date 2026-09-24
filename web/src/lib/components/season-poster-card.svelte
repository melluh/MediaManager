<script lang="ts">
	import MediaImage from '$lib/components/media-image.svelte';
	import { cn } from '$lib/utils';
	import type { ComponentProps } from 'svelte';

	// A season's poster tile with its name, episode count and availability banner.
	// Rendered as the child of a dialog trigger, so it spreads the trigger's props.
	let {
		posterMedia,
		name,
		episodeCount,
		banner,
		...restProps
	}: {
		posterMedia: ComponentProps<typeof MediaImage>['media'];
		name: string;
		episodeCount: number;
		banner: { label: string; classes: string };
		[key: string]: unknown;
	} = $props();
</script>

<button
	type="button"
	{...restProps}
	class="group relative block aspect-2/3 w-full cursor-pointer overflow-hidden rounded-lg bg-muted/50 text-left ring-1 ring-border transition-shadow hover:shadow-lg"
>
	<MediaImage
		media={posterMedia}
		className="h-full w-full object-cover transition-transform duration-200 group-hover:scale-105"
		loading="lazy"
	/>
	<div
		class="absolute inset-0 flex flex-col justify-end gap-0.5 bg-gradient-to-t from-black/90 via-black/40 to-transparent p-2 pb-6 text-left text-white"
	>
		<p class="text-sm leading-tight font-semibold">{name}</p>
		<p class="truncate text-xs text-white/70">{episodeCount} episodes</p>
	</div>
	<div
		class={cn(
			'absolute inset-x-0 bottom-0 z-10 py-1 text-center text-[10px] font-semibold tracking-wide text-white',
			banner.classes
		)}
	>
		{banner.label}
	</div>
</button>
