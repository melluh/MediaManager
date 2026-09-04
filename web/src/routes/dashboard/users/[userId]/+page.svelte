<script lang="ts">
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';
	import { getContext } from 'svelte';
	import { page } from '$app/state';

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	setCrumbs([{ label: 'User' }]);
</script>

<svelte:head>
	<title>User - MediaManager</title>
</svelte:head>

<main class="mx-auto flex w-full flex-1 flex-col items-center gap-2 p-8 text-center">
	<h1 class="text-2xl font-semibold">User details</h1>
	<p class="text-muted-foreground">This page isn't implemented yet.</p>
	<p class="font-mono text-xs text-muted-foreground">{page.params.userId}</p>
</main>
