<script lang="ts">
	import '../app.css';
	import { ModeWatcher } from 'mode-watcher';
	import { Toaster } from '$lib/components/ui/sonner/index.js';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import NavLoadingBar from '$lib/components/nav-loading-bar.svelte';

	let { children } = $props();

	// The static boot splash in app.html covers the window between the first byte
	// and the app actually mounting; from here on the app paints its own loading UI.
	onMount(() => {
		document.getElementById('app-boot-splash')?.remove();
	});
</script>

<svelte:head>
	<title>MediaManager</title>
	<meta content="Smart PVR for movies and TV shows" name="description" />
	<link href={resolve('/logo.svg', {})} rel="icon" type="image/svg" />
</svelte:head>

<NavLoadingBar />
<ModeWatcher />
<Toaster />
{@render children()}
