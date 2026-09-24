<script lang="ts">
	import UserTable from '$lib/components/users/user-table.svelte';
	import StatTile from '$lib/components/admin/stat-tile.svelte';
	import DiskUsageList from '$lib/components/admin/disk-usage-list.svelte';
	import PageHeading from '$lib/components/page-heading.svelte';
	import PageLoading from '$lib/components/page-loading.svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { getCurrentUser, setCrumbs } from '$lib/context.svelte';
	import { Resolved } from '$lib/hooks/resolved.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	setCrumbs([{ label: 'Administration' }]);

	let currentUser = getCurrentUser();

	// This page is admin-only. The backend enforces this on every /admin/*
	// call; this redirect is just so a non-admin who reaches the URL directly
	// doesn't sit on an empty page.
	$effect(() => {
		if (!currentUser().is_superuser) {
			goto(resolve('/dashboard', {}));
		}
	});

	// Resolved in place rather than awaited in markup, so saving a user (which
	// calls invalidateAll()) doesn't remount UserTable and close its dialogs.
	const stats = new Resolved(() => data.stats);
	const diskUsage = new Resolved(() => data.diskUsage);
	const users = new Resolved(() => data.users);
	const passwordLoginEnabled = new Resolved(() => data.passwordLoginEnabled);
</script>

<svelte:head>
	<title>Administration - MediaManager</title>
	<meta content="Server statistics, disk usage, and management tools" name="description" />
</svelte:head>

<main class="mx-auto flex w-full flex-1 flex-col gap-4 p-4 md:max-w-[80em]">
	<PageHeading class="my-6">Administration</PageHeading>

	<section id="stats" class="mt-4 flex flex-col gap-3">
		<h2 class="text-2xl font-semibold">Server Statistics</h2>
		{#if stats.status === 'loading'}
			<PageLoading message="Loading statistics…" />
		{:else if !stats.value}
			<p class="text-sm text-muted-foreground">Could not load server statistics.</p>
		{:else}
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
				<StatTile value={stats.value.movie_count} label="Movies" />
				<StatTile value={stats.value.show_count} label="TV Shows" />
				<StatTile value={stats.value.episode_count} label="Downloaded Episodes" />
			</div>
		{/if}
	</section>

	<section id="disk-usage" class="mt-4 flex flex-col gap-3">
		<h2 class="text-2xl font-semibold">Disk Usage</h2>
		{#if diskUsage.status === 'loading'}
			<PageLoading message="Loading disk usage…" />
		{:else if !diskUsage.value}
			<p class="text-sm text-muted-foreground">Could not load disk usage.</p>
		{:else if diskUsage.value.entries.length === 0}
			<p class="text-sm text-muted-foreground">No configured library paths found.</p>
		{:else}
			<DiskUsageList entries={diskUsage.value.entries} />
		{/if}
	</section>

	<section id="users" class="mt-4 flex flex-col gap-3">
		<div>
			<h2 class="text-2xl font-semibold">Users</h2>
			<p class="text-sm text-muted-foreground">
				Edit, delete or change the permissions of other users
			</p>
		</div>
		{#if users.value === undefined || passwordLoginEnabled.value === undefined}
			<PageLoading message="Loading users…" />
		{:else}
			<UserTable
				currentUserId={currentUser().id}
				passwordLoginEnabled={passwordLoginEnabled.value}
				users={users.value}
			/>
		{/if}
	</section>
</main>
