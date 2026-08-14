<script lang="ts">
	import { cn } from '$lib/utils.js';
	import type { Snippet } from 'svelte';

	let {
		value,
		max = 100,
		size = 36,
		strokeWidth = 4,
		class: className,
		children
	}: {
		value: number;
		max?: number;
		size?: number;
		strokeWidth?: number;
		class?: string;
		children?: Snippet;
	} = $props();

	let radius = $derived((size - strokeWidth) / 2);
	let circumference = $derived(2 * Math.PI * radius);
	let center = $derived(size / 2);
	let progressRatio = $derived(Math.min(1, Math.max(0, max > 0 ? value / max : 0)));
	let dashoffset = $derived(circumference * (1 - progressRatio));
</script>

<div class={cn('relative inline-flex items-center justify-center', className)} style="width: {size}px; height: {size}px;">
	<svg width={size} height={size} viewBox="0 0 {size} {size}">
		<circle
			cx={center}
			cy={center}
			r={radius}
			fill="none"
			stroke-width={strokeWidth}
			class="stroke-primary/20"
		/>
		<circle
			cx={center}
			cy={center}
			r={radius}
			fill="none"
			stroke-width={strokeWidth}
			stroke-linecap="round"
			stroke-dasharray={circumference}
			stroke-dashoffset={dashoffset}
			transform="rotate(-90 {center} {center})"
			class="stroke-primary transition-[stroke-dashoffset] duration-300 ease-out"
		/>
	</svg>
	{#if children}
		<div class="absolute inset-0 flex items-center justify-center">
			{@render children()}
		</div>
	{/if}
</div>
