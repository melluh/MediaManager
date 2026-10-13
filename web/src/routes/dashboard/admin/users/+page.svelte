<script lang="ts">
	import UserTable from '$lib/components/users/user-table.svelte';
	import PageHeading from '$lib/components/page-heading.svelte';
	import PageLoading from '$lib/components/page-loading.svelte';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import { resolve } from '$app/paths';
	import { getCurrentUser, setCrumbs } from '$lib/context.svelte';
	import { Resolved } from '$lib/hooks/resolved.svelte';
	import UserPlus from '@lucide/svelte/icons/user-plus';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	setCrumbs([
		{ label: 'Administration', href: resolve('/dashboard/admin', {}) },
		{ label: 'Users' }
	]);

	let currentUser = getCurrentUser();

	// Resolved in place rather than awaited in markup, so saving a user (which
	// calls invalidateAll()) doesn't remount UserTable and close its dialogs.
	const users = new Resolved(() => data.users);
	const passwordLoginEnabled = new Resolved(() => data.passwordLoginEnabled);

	let pendingCount = $derived(users.value?.filter((u) => !u.is_verified).length ?? 0);
</script>

<svelte:head>
	<title>Users - MediaManager</title>
	<meta content="Edit, delete or change the permissions of other users" name="description" />
</svelte:head>

<main class="mx-auto flex w-full flex-1 flex-col gap-4 p-4 md:max-w-[80em]">
	<PageHeading class="my-6">Users</PageHeading>

	{#if users.value === undefined || passwordLoginEnabled.value === undefined}
		<PageLoading message="Loading users…" />
	{:else}
		<UserTable
			currentUserId={currentUser().id}
			passwordLoginEnabled={passwordLoginEnabled.value}
			users={users.value}
		>
			{#snippet toolbar()}
				{#if pendingCount > 0}
					<a href={resolve('/dashboard/admin/users/pending', {})} class="group">
						<Alert.Root
							class="flex w-auto items-center gap-3 transition-colors group-hover:bg-muted"
						>
							<UserPlus class="size-4 shrink-0" />
							<Alert.Description class="flex-1">
								{pendingCount === 1 ? '1 user is' : `${pendingCount} users are`} waiting for approval
							</Alert.Description>
							<span class="flex items-center gap-1 font-medium">
								Review<ChevronRight class="size-4" />
							</span>
						</Alert.Root>
					</a>
				{/if}
			{/snippet}
		</UserTable>
	{/if}
</main>
