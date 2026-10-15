<script lang="ts">
	import PageLoading from '$lib/components/page-loading.svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import EditUserDialog from '$lib/components/users/edit-user-dialog.svelte';
	import UserRoleBadge from '$lib/components/users/user-role-badge.svelte';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';
	import type { UserRead } from '$lib/api/api';
	import History from '@lucide/svelte/icons/history';
	import Pencil from '@lucide/svelte/icons/pencil';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { setCrumbs } from '$lib/context.svelte';
	import { Resolved } from '$lib/hooks/resolved.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const isAdmin = new Resolved(() => data.isAdmin);
	const user = new Resolved(() => data.user, { key: () => page.params.userId });
	const currentUserId = new Resolved(() => data.currentUserId);
	const passwordLoginEnabled = new Resolved(() => data.passwordLoginEnabled);

	// The dialog edits its own copy, like on the users page; saving refreshes `user`.
	let editedUser: UserRead | null = $state(null);
	const editDialog = shallowDialog('editUser');

	setCrumbs(() =>
		isAdmin.value
			? [
					{ label: 'Administration', href: resolve('/dashboard/admin', {}) },
					{ label: 'Users', href: resolve('/dashboard/admin/users', {}) },
					{ label: user.value?.display_name || user.value?.email || 'User' }
				]
			: [{ label: user.value?.display_name || user.value?.email || 'User' }]
	);
</script>

<svelte:head>
	<title>{user.value?.display_name || user.value?.email || 'User'} - MediaManager</title>
</svelte:head>

{#if isAdmin.value === undefined}
	<PageLoading />
{:else}
	<main class="mx-auto flex w-full flex-1 flex-col gap-4 p-4 md:max-w-[80em]">
		<section class="my-6 flex flex-col gap-2">
			{#if user.value === undefined}
				<PageLoading message="Loading user…" />
			{:else if user.value === null}
				<h1 class="text-2xl font-semibold">Deleted user</h1>
				<p class="text-sm text-muted-foreground">This user no longer exists.</p>
				{#if isAdmin.value}
					<Button
						variant="secondary"
						class="self-start"
						href={resolve('/dashboard/users/[userId]/activity', { userId: page.params.userId! })}
					>
						<History class="mr-2 size-4" />Audit log
					</Button>
				{/if}
			{:else}
				<div class="flex flex-wrap items-center justify-between gap-4">
					<div class="flex flex-wrap items-center gap-3">
						<h1 class="text-3xl font-bold tracking-tight">
							{user.value.display_name || user.value.email}
						</h1>
						{#if user.value.is_superuser}
							<UserRoleBadge user={user.value} />
						{/if}
					</div>
					{#if isAdmin.value}
						<div class="flex flex-wrap gap-2">
							<Button
								variant="secondary"
								href={resolve('/dashboard/users/[userId]/activity', {
									userId: page.params.userId!
								})}
							>
								<History class="mr-2 size-4" />Audit log
							</Button>
							<Button
								variant="secondary"
								onclick={() => {
									// Admins load the full user, so this is a `UserRead`.
									editedUser = (user.value as UserRead | null) ?? null;
									editDialog.open = true;
								}}
							>
								<Pencil class="mr-2 size-4" />Edit user
							</Button>
						</div>
					{/if}
				</div>
			{/if}
		</section>

		{#if isAdmin.value}
			<EditUserDialog
				bind:user={editedUser}
				bind:open={editDialog.open}
				passwordLoginEnabled={passwordLoginEnabled.value ?? true}
				isSelf={editedUser?.id === currentUserId.value}
			/>
		{/if}
	</main>
{/if}
