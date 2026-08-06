<script lang="ts">
	import * as Card from '$lib/components/ui/card/index.js';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { cn, formatRuntime } from '$lib/utils';
	import type { Snippet } from 'svelte';

	let {
		name,
		year = null,
		runtime = null,
		genres = [],
		posterLoaded = true,
		poster,
		indicators,
		href,
		triggerProps,
		class: className = '',
		onmouseenter,
		onfocus
	}: {
		name: string;
		year?: number | null;
		runtime?: number | null;
		genres?: string[] | null;
		posterLoaded?: boolean;
		poster: Snippet;
		indicators?: Snippet;
		href?: string;
		triggerProps?: Record<string, unknown>;
		class?: string;
		onmouseenter?: () => void;
		onfocus?: () => void;
	} = $props();
</script>

<Card.Root class={cn('group col-span-full overflow-hidden sm:col-span-1', className)}>
	<svelte:element
		this={href ? 'a' : 'button'}
		href={href as never}
		class="relative block aspect-2/3 w-full cursor-pointer overflow-hidden rounded-xl text-left"
		{onmouseenter}
		{onfocus}
		{...triggerProps}
	>
		{@render poster()}
		{#if !posterLoaded}
			<Skeleton class="absolute inset-0 h-full w-full" />
		{/if}
		{#if indicators}
			<div class="absolute top-2 right-2 z-10 flex flex-col items-end gap-1">
				{@render indicators()}
			</div>
		{/if}
		<div
			class="absolute inset-0 flex flex-col justify-end gap-1 bg-gradient-to-t from-black/90 via-black/40 to-transparent p-3 text-white opacity-0 transition-opacity duration-200 group-focus-within:opacity-100 group-hover:opacity-100"
		>
			<div class="flex items-start justify-between gap-2">
				<p class="leading-tight font-semibold">
					{name}
					{#if year != null}
						<span class="font-normal text-white/70">({year})</span>
					{/if}
				</p>
				<ChevronRight class="h-5 w-5 shrink-0 text-white/80" />
			</div>
			<div class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-white/80">
				{#if formatRuntime(runtime)}
					<span>{formatRuntime(runtime)}</span>
				{/if}
				{#if genres && genres.length > 0}
					<span>{genres.slice(0, 3).join(', ')}</span>
				{/if}
			</div>
		</div>
	</svelte:element>
</Card.Root>
