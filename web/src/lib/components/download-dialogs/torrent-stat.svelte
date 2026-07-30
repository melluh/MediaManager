<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		icon: Icon,
		label,
		value,
		children
	}: {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		icon: any;
		label: string;
		value?: string;
		children?: Snippet;
	} = $props();
</script>

<div class="flex min-w-28 flex-1 items-center gap-2.5 rounded-lg border bg-muted/40 px-3 py-2">
	<Icon class="size-4 shrink-0 text-muted-foreground" />
	<div class="min-w-0">
		<div class="text-xs text-muted-foreground">{label}</div>
		<div class="truncate text-sm font-medium">
			{#if children}
				{@render children()}
			{:else}
				{value}
			{/if}
		</div>
	</div>
</div>
