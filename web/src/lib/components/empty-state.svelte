<script lang="ts">
	import type { Component, Snippet } from 'svelte';
	import { cn } from '$lib/utils';

	let {
		icon: Icon,
		title,
		destructive = false,
		class: className,
		children
	}: {
		icon: Component<{ class?: string }>;
		title: string;
		destructive?: boolean;
		class?: string;
		/** The explanation under the title. */
		children?: Snippet;
	} = $props();
</script>

<div
	class={cn(
		'flex flex-col items-center gap-1 rounded-lg border border-dashed px-3 py-6 text-center',
		destructive && 'border-destructive/50 bg-destructive/10',
		className
	)}
>
	<Icon class={cn('size-8', destructive ? 'text-destructive' : 'text-muted-foreground')} />
	<p class={cn('text-sm font-medium', destructive && 'text-destructive')}>{title}</p>
	{#if children}
		<p class="text-xs text-muted-foreground">{@render children()}</p>
	{/if}
</div>
