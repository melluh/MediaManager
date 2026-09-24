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

<div
	class={cn(
		'grid w-full auto-rows-min gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5',
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
