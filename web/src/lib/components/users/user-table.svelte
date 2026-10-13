<script lang="ts">
	import * as Table from '$lib/components/ui/table/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import UserRoleBadge from '$lib/components/users/user-role-badge.svelte';
	import UserStatusBadge from '$lib/components/users/user-status-badge.svelte';
	import UserPill from '$lib/components/user-pill.svelte';
	import CreateUserDialog from '$lib/components/users/create-user-dialog.svelte';
	import EditUserDialog from '$lib/components/users/edit-user-dialog.svelte';
	import DeleteUserDialog from '$lib/components/users/delete-user-dialog.svelte';
	import AcceptUserDialog from '$lib/components/users/accept-user-dialog.svelte';
	import type { UserRead } from '$lib/api/api';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Check from '@lucide/svelte/icons/check';
	import X from '@lucide/svelte/icons/x';
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
	let pendingUsers = $derived(sortedUsers.filter((u) => !u.is_verified));
	let verifiedUsers = $derived(sortedUsers.filter((u) => u.is_verified));

	let selectedUser: UserRead | null = $state(null);
	let userToReject: UserRead | null = $state(null);
	let userToAccept: UserRead | null = $state(null);
	const editDialog = shallowDialog('editUser');
	const rejectDialog = shallowDialog('rejectUser');
	const acceptDialog = shallowDialog('acceptUser');
</script>

<div class="mb-4 flex justify-end">
	<CreateUserDialog {passwordLoginEnabled} />
</div>

{#if pendingUsers.length > 0}
	<section class="mb-8">
		<h3 class="mb-2 text-lg font-semibold">Pending approval</h3>
		<Table.Root>
			<Table.Caption>Users who signed up and are waiting to be accepted.</Table.Caption>
			<Table.Header>
				<Table.Row>
					<Table.Head>Email</Table.Head>
					<Table.Head></Table.Head>
				</Table.Row>
			</Table.Header>
			<Table.Body>
				{#each pendingUsers as user (user.id)}
					<Table.Row>
						<Table.Cell>
							<div class="flex items-center gap-2">
								<span>{user.email}</span>
								<Tooltip.Root>
									<Tooltip.Trigger>
										{#snippet child({ props })}
											<Badge {...props} variant="outline" class="cursor-help">Unverified</Badge>
										{/snippet}
									</Tooltip.Trigger>
									<Tooltip.Content class="max-w-xs">
										This is the email address entered at sign-up. It hasn't been confirmed in any
										way, so make sure you recognise this person before accepting.
									</Tooltip.Content>
								</Tooltip.Root>
							</div>
						</Table.Cell>
						<Table.Cell>
							<div class="flex justify-end gap-2">
								<Button
									onclick={() => {
										userToAccept = user;
										acceptDialog.open = true;
									}}
								>
									<Check class="mr-2 size-4" />Accept
								</Button>
								<Button
									variant="destructive"
									onclick={() => {
										userToReject = user;
										rejectDialog.open = true;
									}}
								>
									<X class="mr-2 size-4" />Reject
								</Button>
							</div>
						</Table.Cell>
					</Table.Row>
				{/each}
			</Table.Body>
		</Table.Root>
	</section>
{/if}

<Table.Root>
	<Table.Caption>A list of all users.</Table.Caption>
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
<DeleteUserDialog user={userToReject} bind:open={rejectDialog.open} />
<AcceptUserDialog user={userToAccept} bind:open={acceptDialog.open} />
