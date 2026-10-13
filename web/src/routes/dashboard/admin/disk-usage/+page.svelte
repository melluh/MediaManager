<script lang="ts">
	import DiskUsageList from '$lib/components/admin/disk-usage-list.svelte';
	import PageHeading from '$lib/components/page-heading.svelte';
	import PageLoading from '$lib/components/page-loading.svelte';
	import { resolve } from '$app/paths';
	import { setCrumbs } from '$lib/context.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	setCrumbs([
		{ label: 'Administration', href: resolve('/dashboard/admin', {}) },
		{ label: 'Disk Usage' }
	]);
</script>

<svelte:head>
	<title>Disk Usage - MediaManager</title>
	<meta content="Storage used by your library paths" name="description" />
</svelte:head>

<main class="mx-auto flex w-full flex-1 flex-col gap-4 p-4 md:max-w-[80em]">
	<PageHeading class="my-6">Disk Usage</PageHeading>

	{#await data.diskUsage}
		<PageLoading message="Loading disk usage…" />
	{:then diskUsage}
		{#if !diskUsage}
			<p class="text-sm text-muted-foreground">Could not load disk usage.</p>
		{:else if diskUsage.entries.length === 0}
			<p class="text-sm text-muted-foreground">No configured library paths found.</p>
		{:else}
			<DiskUsageList entries={diskUsage.entries} />
		{/if}
	{/await}
</main>
