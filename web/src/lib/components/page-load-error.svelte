<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import ServerCrash from '@lucide/svelte/icons/server-crash';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import { invalidateAll } from '$app/navigation';

	let {
		title = 'Something went wrong',
		message = 'Could not reach the MediaManager backend. Please try again in a moment.',
		fullPage = false
	}: { title?: string; message?: string; fullPage?: boolean } = $props();

	let retrying = $state(false);

	async function retry() {
		retrying = true;
		try {
			await invalidateAll();
		} finally {
			retrying = false;
		}
	}
</script>

<div
	class="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center {fullPage
		? 'min-h-svh w-full'
		: 'min-h-64'}"
>
	<ServerCrash class="size-12 text-muted-foreground" />
	<div>
		<h2 class="text-xl font-semibold tracking-tight">{title}</h2>
		<p class="mt-1 max-w-md text-sm text-muted-foreground">{message}</p>
	</div>
	<Button variant="outline" onclick={retry} disabled={retrying}>
		<RefreshCw class="size-4 {retrying ? 'animate-spin' : ''}" />
		Try again
	</Button>
</div>
