<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { Spinner } from '$lib/components/ui/spinner';

	onMount(() => {
		goto(resolve('/dashboard', {}));
	});
</script>

<svelte:head>
	<title>MediaManager - Smart PVR for Movies and TV Shows</title>
	<meta
		content="Smart PVR for movies and TV shows - Your personal media management solution"
		name="description"
	/>
</svelte:head>

<div class="flex h-screen w-screen flex-col items-center justify-center gap-3">
	<Spinner class="size-8" />
	<p class="text-sm text-muted-foreground">Loading MediaManager…</p>
</div>
