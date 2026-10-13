<script lang="ts">
	import * as Table from '$lib/components/ui/table/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import UserRoleBadge from '$lib/components/users/user-role-badge.svelte';
	import UserStatusBadge from '$lib/components/users/user-status-badge.svelte';
	import UserPill from '$lib/components/user-pill.svelte';
	import CreateUserDialog from '$lib/components/users/create-user-dialog.svelte';
	import EditUserDialog from '$lib/components/users/edit-user-dialog.svelte';
	import type { UserRead } from '$lib/api/api';
	import Pencil from '@lucide/svelte/icons/pencil';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';
	import type { Snippet } from 'svelte';

	let {
		users,
		currentUserId,
		passwordLoginEnabled = true,
		toolbar
	}: {
		users: UserRead[];
		currentUserId: string;
		passwordLoginEnabled?: boolean;
		// Rendered at the start of the row holding the "Add user" button.
		toolbar?: Snippet;
	} = $props();
	let sortedUsers = $derived(
		[...users].sort((a, b) => {
			if (a.id === currentUserId) return -1;
			if (b.id === currentUserId) return 1;
			return a.email.localeCompare(b.email);
		})
	);
	let verifiedUsers = $derived(sortedUsers.filter((u) => u.is_verified));

	let selectedUser: UserRead | null = $state(null);
	const editDialog = shallowDialog('editUser');
</script>

<div class="mb-4 flex flex-wrap items-center gap-4">
	{@render toolbar?.()}
	<div class="ml-auto">
		<CreateUserDialog {passwordLoginEnabled} />
	</div>
</div>

<Table.Root>
	<Table.Header>
		<Table.Row>
			<Table.Head>User</Table.Head>
			<Table.Head>Status</Table.Head>
			<Table.Head>Role</Table.Head>
		</Table.Row>
	</Table.Header>
	<Table.Body>
		{#each verifiedUsers as user (user.id)}
			<Table.Row>
				<Table.Cell class="font-medium">
					<UserPill
						userId={user.id}
						name={user.display_name || user.email}
						isAdmin={user.is_superuser}
					/>
				</Table.Cell>
				<Table.Cell>
					<UserStatusBadge {user} />
				</Table.Cell>
				<Table.Cell>
					<UserRoleBadge {user} />
				</Table.Cell>
				<Table.Cell>
					{#if user.id === currentUserId}
						<span class="text-sm text-muted-foreground italic">This is your own account</span>
					{:else}
						<div class="flex gap-2">
							<Button
								variant="secondary"
								onclick={() => {
									selectedUser = user;
									editDialog.open = true;
								}}
							>
								<Pencil class="mr-2 size-4" />Edit
							</Button>
						</div>
					{/if}
				</Table.Cell>
			</Table.Row>
		{/each}
	</Table.Body>
</Table.Root>
<EditUserDialog bind:user={selectedUser} bind:open={editDialog.open} {passwordLoginEnabled} />
