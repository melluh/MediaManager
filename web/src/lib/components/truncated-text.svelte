<script lang="ts">
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import { cn } from '$lib/utils';

	let {
		text,
		tooltip = text,
		class: className
	}: {
		text: string;
		tooltip?: string;
		class?: string;
	} = $props();

	let el = $state<HTMLElement | null>(null);
	let open = $state(false);

	// Only show the tooltip when the text is actually cut off by the ellipsis.
	const isTruncated = () => !!el && el.scrollWidth > el.clientWidth;
</script>

<Tooltip.Root bind:open={() => open, (v) => (open = v && isTruncated())} disableHoverableContent>
	<Tooltip.Trigger>
		{#snippet child({ props })}
			<span {...props} bind:this={el} class={cn('block truncate', className)}>{text}</span>
		{/snippet}
	</Tooltip.Trigger>
	<Tooltip.Content class="max-w-[min(90vw,48rem)] font-mono break-all">
		{tooltip}
	</Tooltip.Content>
</Tooltip.Root>
