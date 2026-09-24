<script lang="ts">
	import Check from '@lucide/svelte/icons/check';
	import Copy from '@lucide/svelte/icons/copy';
	import { Clipboard } from '$lib/hooks/clipboard.svelte';
	import { cn } from '$lib/utils';

	let { text, class: className }: { text: string; class?: string } = $props();

	const clipboard = new Clipboard();
</script>

<button
	type="button"
	onclick={() => clipboard.copy(text)}
	class={cn(
		'flex shrink-0 items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-normal hover:bg-current/10',
		className
	)}
>
	{#if clipboard.copied}
		<Check class="size-3" />
		Copied
	{:else}
		<Copy class="size-3" />
		Copy
	{/if}
</button>
