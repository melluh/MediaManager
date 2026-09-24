<script lang="ts">
	import UserTable from '$lib/components/user-data-table.svelte';
	import { Progress } from '$lib/components/ui/progress/index.js';
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import type {
		DiskUsageStats,
		LibraryStats,
		UserRead,
		UserReadWithPermissions
	} from '$lib/api/api';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';
	import PageLoading from '$lib/components/page-loading.svelte';
	import { formatBytes } from '$lib/utils';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	setCrumbs([{ label: 'Administration' }]);

	let currentUser: () => UserReadWithPermissions = getContext('user');

	// This page is admin-only. The backend enforces this on every /admin/*
	// call; this redirect is just so a non-admin who reaches the URL directly
	// doesn't sit on an empty page.
	$effect(() => {
		if (!currentUser().is_superuser) {
			goto(resolve('/dashboard', {}));
		}
	});

	// `data.*` are re-created as new promises on every invalidateAll() (e.g.
	// after editing a user). Awaiting them directly in the markup would remount
	// UserTable on every save, wiping its local state (like an open edit
	// dialog). Instead resolve into local state once and update in place.
	let stats: LibraryStats | null | undefined = $state();
	let diskUsage: DiskUsageStats | null | undefined = $state();
	let users: UserRead[] | undefined = $state();
	let passwordLoginEnabled: boolean | undefined = $state();

	$effect(() => {
		const promise = data.stats;
		promise.then((s) => {
			if (promise === data.stats) stats = s;
		});
	});
	$effect(() => {
		const promise = data.diskUsage;
		promise.then((d) => {
			if (promise === data.diskUsage) diskUsage = d;
		});
	});
	$effect(() => {
		const promise = data.users;
		promise.then((u) => {
			if (promise === data.users) users = u;
		});
	});
	$effect(() => {
		const promise = data.passwordLoginEnabled;
		promise.then((p) => {
			if (promise === data.passwordLoginEnabled) passwordLoginEnabled = p;
		});
	});
</script>

<svelte:head>
	<title>Administration - MediaManager</title>
	<meta content="Server statistics, disk usage, and management tools" name="description" />
</svelte:head>

<main class="mx-auto flex w-full flex-1 flex-col gap-4 p-4 md:max-w-[80em]">
	<h1 class="my-6 scroll-m-20 text-center text-4xl font-extrabold tracking-tight lg:text-5xl">
		Administration
	</h1>

	<section id="stats" class="mt-4 flex flex-col gap-3">
		<h2 class="text-2xl font-semibold">Server Statistics</h2>
		{#if stats === undefined}
			<PageLoading message="Loading statistics…" />
		{:else if stats === null}
			<p class="text-sm text-muted-foreground">Could not load server statistics.</p>
		{:else}
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
				<div class="rounded-lg border p-4 text-center">
					<p class="text-3xl font-bold">{stats.movie_count}</p>
					<p class="text-sm text-muted-foreground">Movies</p>
				</div>
				<div class="rounded-lg border p-4 text-center">
					<p class="text-3xl font-bold">{stats.show_count}</p>
					<p class="text-sm text-muted-foreground">TV Shows</p>
				</div>
				<div class="rounded-lg border p-4 text-center">
					<p class="text-3xl font-bold">{stats.episode_count}</p>
					<p class="text-sm text-muted-foreground">Downloaded Episodes</p>
				</div>
			</div>
		{/if}
	</section>

	<section id="disk-usage" class="mt-4 flex flex-col gap-3">
		<h2 class="text-2xl font-semibold">Disk Usage</h2>
		{#if diskUsage === undefined}
			<PageLoading message="Loading disk usage…" />
		{:else if diskUsage === null}
			<p class="text-sm text-muted-foreground">Could not load disk usage.</p>
		{:else if diskUsage.entries.length === 0}
			<p class="text-sm text-muted-foreground">No configured library paths found.</p>
		{:else}
			<div class="flex flex-col gap-4">
				{#each diskUsage.entries as entry (entry.paths.join(','))}
					<div>
						<div class="mb-1 flex items-baseline justify-between gap-2">
							<span class="font-medium">{entry.names.join(', ')}</span>
							{#if entry.available}
								<span class="shrink-0 text-sm text-muted-foreground">
									{formatBytes(entry.used_bytes)} / {formatBytes(entry.total_bytes)} used
								</span>
							{:else}
								<span class="shrink-0 text-sm text-destructive">Path not found</span>
							{/if}
						</div>
						{#if entry.available}
							<Progress
								value={entry.total_bytes > 0 ? (entry.used_bytes / entry.total_bytes) * 100 : 0}
							/>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</section>

	<section id="users" class="mt-4 flex flex-col gap-3">
		<div>
			<h2 class="text-2xl font-semibold">Users</h2>
			<p class="text-sm text-muted-foreground">
				Edit, delete or change the permissions of other users
			</p>
		</div>
		{#if users === undefined || passwordLoginEnabled === undefined}
			<PageLoading message="Loading users…" />
		{:else}
			<UserTable currentUserId={currentUser().id} {passwordLoginEnabled} {users} />
		{/if}
	</section>
</main>
