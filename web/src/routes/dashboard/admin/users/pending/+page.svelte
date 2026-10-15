<script lang="ts">
	import PendingUserTable from '$lib/components/users/pending-user-table.svelte';
	import PageHeading from '$lib/components/page-heading.svelte';
	import PageLoading from '$lib/components/page-loading.svelte';
	import { resolve } from '$app/paths';
	import { setCrumbs } from '$lib/context.svelte';
	import { Resolved } from '$lib/hooks/resolved.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	setCrumbs([
		{ label: 'Administration', href: resolve('/dashboard/admin', {}) },
		{ label: 'Users', href: resolve('/dashboard/admin/users', {}) },
		{ label: 'Pending approval' }
	]);

	// Resolved in place rather than awaited in markup, so accepting a user (which
	// calls refreshAll()) doesn't remount PendingUserTable and close its dialogs.
	const users = new Resolved(() => data.users);

	let pendingUsers = $derived(
		(users.value ?? []).filter((u) => !u.is_verified).sort((a, b) => a.email.localeCompare(b.email))
	);
</script>

<svelte:head>
	<title>Pending Approval - MediaManager</title>
	<meta content="Users who signed up and are waiting to be accepted" name="description" />
</svelte:head>

<main class="mx-auto flex w-full flex-1 flex-col gap-4 p-4 md:max-w-[80em] tablet:px-8">
	<PageHeading class="my-6">Pending approval</PageHeading>

	{#if users.value === undefined}
		<PageLoading message="Loading users…" />
	{:else if pendingUsers.length === 0}
		<p class="text-sm text-muted-foreground">No users are waiting for approval.</p>
	{:else}
		<PendingUserTable users={pendingUsers} />
	{/if}
</main>
