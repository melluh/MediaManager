<script lang="ts">
	import StatTile from '$lib/components/admin/stat-tile.svelte';
	import PageHeading from '$lib/components/page-heading.svelte';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { resolve } from '$app/paths';
	import { setCrumbs } from '$lib/context.svelte';
	import HardDrive from '@lucide/svelte/icons/hard-drive';
	import History from '@lucide/svelte/icons/history';
	import Users from '@lucide/svelte/icons/users';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	setCrumbs([{ label: 'Administration' }]);

	const sections = [
		{
			title: 'Disk Usage',
			description: 'Storage used by your library paths',
			path: '/dashboard/admin/disk-usage',
			icon: HardDrive
		},
		{
			title: 'Users',
			description: 'Edit, delete or change the permissions of other users',
			path: '/dashboard/admin/users',
			icon: Users
		},
		{
			title: 'Activity',
			description: 'What users have done, and when',
			path: '/dashboard/admin/activity',
			icon: History
		}
	] as const;
</script>

<svelte:head>
	<title>Administration - MediaManager</title>
	<meta content="Server statistics and management tools" name="description" />
</svelte:head>

<main class="mx-auto flex w-full flex-1 flex-col gap-4 p-4 md:max-w-[80em]">
	<PageHeading class="my-6">Administration</PageHeading>

	<section id="stats" class="mt-4 flex flex-col gap-3">
		<h2 class="text-2xl font-semibold">Server Statistics</h2>
		{#await data.stats}
			<div class="grid grid-cols-3 gap-2 md:gap-4">
				{#each ['Movies', 'TV Shows', 'Downloaded Episodes'] as label (label)}
					<div class="rounded-lg border p-2 text-center md:p-4">
						<Skeleton class="mx-auto h-8 w-12 md:h-9" />
						<p class="text-xs text-muted-foreground md:text-sm">{label}</p>
					</div>
				{/each}
			</div>
		{:then stats}
			{#if !stats}
				<p class="text-sm text-muted-foreground">Could not load server statistics.</p>
			{:else}
				<div class="grid grid-cols-3 gap-2 md:gap-4">
					<StatTile value={stats.movie_count} label="Movies" />
					<StatTile value={stats.show_count} label="TV Shows" />
					<StatTile value={stats.episode_count} label="Downloaded Episodes" />
				</div>
			{/if}
		{/await}
	</section>

	<section id="manage" class="mt-4 flex flex-col gap-3">
		<h2 class="text-2xl font-semibold">Manage</h2>
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			{#each sections as section (section.path)}
				<a
					href={resolve(section.path, {})}
					class="flex items-center gap-4 rounded-lg border p-4 transition-colors hover:bg-muted"
				>
					<section.icon class="size-6 shrink-0 text-muted-foreground" />
					<div class="flex-1">
						<p class="font-semibold">{section.title}</p>
						<p class="text-sm text-muted-foreground">{section.description}</p>
					</div>
					<ChevronRight class="size-4 shrink-0 text-muted-foreground" />
				</a>
			{/each}
		</div>
	</section>
</main>
