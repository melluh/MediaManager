<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import { Spinner } from '$lib/components/ui/spinner';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';

	let { rescanning, onclick }: { rescanning: boolean; onclick: () => void } = $props();
</script>

<Button variant="outline" size="sm" {onclick} disabled={rescanning}>
	{#if rescanning}
		<Spinner class="size-4" />
	{:else}
		<RefreshCw class="size-4" />
	{/if}
	Rescan
</Button>
