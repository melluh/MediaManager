<script lang="ts">
	import UserTable from '$lib/components/user-data-table.svelte';
	import * as Card from '$lib/components/ui/card/index.js';
	import { getContext } from 'svelte';
	import UserSettings from '$lib/components/user-settings.svelte';
	import type { UserRead, UserReadWithPermissions } from '$lib/api/api';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';
	import PageLoading from '$lib/components/page-loading.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	setCrumbs([{ label: 'Settings' }]);

	let currentUser: () => UserReadWithPermissions = getContext('user');

	// `data.users`/`data.passwordLoginEnabled` are re-created as new promises on every
	// invalidateAll() (e.g. after editing a user). Awaiting them directly in the markup
	// would remount UserSettings/UserTable on every save, wiping their local state (like
	// an open edit dialog). Instead resolve into local state once and update in place.
	let users: UserRead[] | undefined = $state();
	let passwordLoginEnabled: boolean | undefined = $state();

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
	<title>Settings - MediaManager</title>
	<meta content="Manage your MediaManager settings and user preferences" name="description" />
</svelte:head>

<main class="mx-auto flex w-full flex-1 flex-col gap-4 p-4 md:max-w-[80em]">
	<h1 class="my-6 scroll-m-20 text-center text-4xl font-extrabold tracking-tight lg:text-5xl">
		Settings
	</h1>
	<Card.Root id="me">
		<Card.Header>
			<Card.Title>Your account</Card.Title>
		</Card.Header>
		<Card.Content>
			{#if passwordLoginEnabled === undefined}
				<PageLoading message="Loading account settings…" />
			{:else}
				<UserSettings {passwordLoginEnabled} />
			{/if}
		</Card.Content>
	</Card.Root>
	{#if currentUser().is_superuser}
		<Card.Root id="users">
			<Card.Header>
				<Card.Title>Users</Card.Title>
				<Card.Description>Edit, delete or change the permissions of other users</Card.Description>
			</Card.Header>
			<Card.Content>
				{#if users === undefined || passwordLoginEnabled === undefined}
					<PageLoading message="Loading users…" />
				{:else}
					<UserTable currentUserId={currentUser().id} {passwordLoginEnabled} {users} />
				{/if}
			</Card.Content>
		</Card.Root>
	{/if}
</main>
