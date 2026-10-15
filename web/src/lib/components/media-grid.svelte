<script lang="ts">
	import type { Snippet } from 'svelte';
	import MediaCardSkeleton from '$lib/components/media-card-skeleton.svelte';
	import { cn } from '$lib/utils';

	let {
		skeletons = 0,
		class: className,
		children
	}: {
		/** Renders this many card skeletons instead of `children`, while loading. */
		skeletons?: number;
		class?: string;
		children?: Snippet;
	} = $props();
</script>

<!-- Tablets get smaller posters than the desktop column counts would give
     them: 3 across in portrait, and 5 in landscape (touch screens at the
     desktop breakpoint). -->
<div
	class={cn(
		'grid w-full auto-rows-min grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 lg:pointer-coarse:grid-cols-5',
		className
	)}
>
	{#if skeletons > 0}
		{#each { length: skeletons }}
			<MediaCardSkeleton />
		{/each}
	{:else}
		{@render children?.()}
	{/if}
</div>
