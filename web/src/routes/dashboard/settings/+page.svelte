<script lang="ts">
	import UserTable from '$lib/components/user-data-table.svelte';
	import { page } from '$app/state';
	import * as Card from '$lib/components/ui/card/index.js';
	import { getContext } from 'svelte';
	import UserSettings from '$lib/components/user-settings.svelte';
	import type { UserRead } from '$lib/api/api';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	setCrumbs([{ label: 'Settings' }]);

	let currentUser: () => UserRead = getContext('user');
	let users: UserRead[] = $derived(
		page.data.users.filter((user: UserRead) => user.id !== currentUser().id)
	);
</script>

<svelte:head>
	<title>Settings - MediaManager</title>
	<meta content="Manage your MediaManager settings and user preferences" name="description" />
</svelte:head>

<main class="mx-auto flex w-full flex-1 flex-col gap-4 p-4 md:max-w-[80em]">
	<h1 class="my-6 scroll-m-20 text-center text-4xl font-extrabold tracking-tight lg:text-5xl">
		Settings
	</h1>
	<Card.Root id="me">
		<Card.Header>
			<Card.Title>You</Card.Title>
			<Card.Description>Change your email or password</Card.Description>
		</Card.Header>
		<Card.Content>
			<UserSettings />
		</Card.Content>
	</Card.Root>
	{#if currentUser().is_superuser}
		<Card.Root id="users">
			<Card.Header>
				<Card.Title>Users</Card.Title>
				<Card.Description>Edit, delete or change the permissions of other users</Card.Description>
			</Card.Header>
			<Card.Content>
				<UserTable {users} />
			</Card.Content>
		</Card.Root>
	{/if}
</main>
