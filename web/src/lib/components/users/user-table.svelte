<script lang="ts">
	import CheckmarkX from '$lib/components/checkmark-x.svelte';
	import * as Table from '$lib/components/ui/table/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import UserPill from '$lib/components/user-pill.svelte';
	import CreateUserDialog from '$lib/components/users/create-user-dialog.svelte';
	import EditUserDialog from '$lib/components/users/edit-user-dialog.svelte';
	import DeleteUserDialog from '$lib/components/users/delete-user-dialog.svelte';
	import type { UserRead } from '$lib/api/api';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';

	let {
		users,
		currentUserId,
		passwordLoginEnabled = true
	}: { users: UserRead[]; currentUserId: string; passwordLoginEnabled?: boolean } = $props();
	let sortedUsers = $derived(
		[...users].sort((a, b) => {
			if (a.id === currentUserId) return -1;
			if (b.id === currentUserId) return 1;
			return a.email.localeCompare(b.email);
		})
	);
	let selectedUser: UserRead | null = $state(null);
	let userToDelete: UserRead | null = $state(null);
	const editDialog = shallowDialog('editUser');
	const deleteDialog = shallowDialog('deleteUser');
</script>

<div class="mb-4 flex justify-end">
	<CreateUserDialog {passwordLoginEnabled} />
</div>
<Table.Root>
	<Table.Caption>A list of all users.</Table.Caption>
	<Table.Header>
		<Table.Row>
			<Table.Head>User</Table.Head>
			<Table.Head>Verified</Table.Head>
			<Table.Head>Active</Table.Head>
			<Table.Head>Admin</Table.Head>
		</Table.Row>
	</Table.Header>
	<Table.Body>
		{#each sortedUsers as user (user.id)}
			<Table.Row>
				<Table.Cell class="font-medium">
					<UserPill userId={user.id} name={user.display_name || user.email} />
				</Table.Cell>
				<Table.Cell>
					<CheckmarkX state={user.is_verified} />
				</Table.Cell>
				<Table.Cell>
					<CheckmarkX state={user.is_active} />
				</Table.Cell>
				<Table.Cell>
					<CheckmarkX state={user.is_superuser} />
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
							<Button
								variant="destructive"
								onclick={() => {
									userToDelete = user;
									deleteDialog.open = true;
								}}
							>
								<Trash2 class="mr-2 size-4" />Delete
							</Button>
						</div>
					{/if}
				</Table.Cell>
			</Table.Row>
		{/each}
	</Table.Body>
</Table.Root>
<EditUserDialog bind:user={selectedUser} bind:open={editDialog.open} {passwordLoginEnabled} />
<DeleteUserDialog user={userToDelete} bind:open={deleteDialog.open} />
