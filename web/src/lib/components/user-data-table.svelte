<script lang="ts">
	import CheckmarkX from '$lib/components/checkmark-x.svelte';
	import * as Table from '$lib/components/ui/table/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { toast } from 'svelte-sonner';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import InlineEditField from '$lib/components/inline-edit-field.svelte';
	import ToggleField from '$lib/components/toggle-field.svelte';
	import ChangePasswordDialog from '$lib/components/change-password-dialog.svelte';
	import UserPill from '$lib/components/user-pill.svelte';
	import { refreshAll } from '$app/navigation';
	import client from '$lib/api';
	import type { UserRead } from '$lib/api/api';
	import UserPlus from '@lucide/svelte/icons/user-plus';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import X from '@lucide/svelte/icons/x';
	import Check from '@lucide/svelte/icons/check';
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
	const createDialog = shallowDialog('createUser');
	let createEmail: string = $state('');
	let createDisplayName: string = $state('');
	let createPassword: string = $state('');
	let createIsSuperuser: boolean = $state(false);
	let isCreating: boolean = $state(false);
	let isDeleting: boolean = $state(false);

	function resetCreateForm() {
		createEmail = '';
		createDisplayName = '';
		createPassword = '';
		createIsSuperuser = false;
	}

	// Closing a shallow-routed dialog goes through an async history.back(), and it can be
	// closed from several places (Cancel, Escape, an overlay click, or a successful
	// submit), so cleanup is centralized here rather than duplicated at each call site.
	// This also keeps loading state (isCreating/isDeleting) visible for the whole time the
	// dialog is still on screen, instead of flipping back to normal before it closes.
	$effect(() => {
		if (!createDialog.open) {
			resetCreateForm();
			isCreating = false;
		}
	});
	$effect(() => {
		if (!deleteDialog.open) {
			userToDelete = null;
			isDeleting = false;
		}
	});

	async function createUser() {
		if (isCreating) return;
		isCreating = true;
		const { error } = await client.POST('/api/v1/users/', {
			body: {
				email: createEmail,
				display_name: createDisplayName || null,
				password: createPassword || null,
				is_superuser: createIsSuperuser,
				is_verified: true
			}
		});
		if (error) {
			toast.error(`Failed to create user: ${error.detail ?? error}`);
			isCreating = false;
			return;
		}
		toast.success(`User ${createEmail} created successfully.`);
		await refreshAll();
		createDialog.open = false;
	}

	async function saveDisplayName(newDisplayName: string): Promise<boolean> {
		if (!selectedUser) return false;
		const { error } = await client.PATCH('/api/v1/users/{id}', {
			params: { path: { id: selectedUser.id } },
			body: { display_name: newDisplayName }
		});
		if (error) {
			toast.error('Failed to update display name');
			return false;
		}
		toast.success('Display name updated successfully.');
		selectedUser.display_name = newDisplayName;
		await refreshAll();
		return true;
	}

	async function saveEmail(newEmail: string): Promise<boolean> {
		if (!selectedUser) return false;
		const { error } = await client.PATCH('/api/v1/users/{id}', {
			params: { path: { id: selectedUser.id } },
			body: { email: newEmail }
		});
		if (error) {
			toast.error('Failed to update email');
			return false;
		}
		toast.success('Email updated successfully.');
		selectedUser.email = newEmail;
		await refreshAll();
		return true;
	}

	async function saveToggle(field: 'is_verified' | 'is_active' | 'is_superuser', value: boolean) {
		if (!selectedUser) return;
		const previousValue = selectedUser[field];
		selectedUser[field] = value;
		const { error } = await client.PATCH('/api/v1/users/{id}', {
			params: { path: { id: selectedUser.id } },
			body: { [field]: value }
		});
		if (error) {
			selectedUser[field] = previousValue;
			toast.error(`Failed to update user ${selectedUser.email}`);
			return;
		}
		toast.success(`User ${selectedUser.email} updated successfully.`);
		await refreshAll();
	}

	async function deleteUser() {
		if (!userToDelete || isDeleting) return;
		isDeleting = true;

		const { error } = await client.DELETE('/api/v1/users/{id}', {
			params: {
				path: {
					id: userToDelete.id
				}
			}
		});

		if (error) {
			toast.error(`Failed to delete user ${userToDelete.email}: ${error}`);
			isDeleting = false;
			return;
		}
		toast.success(`User ${userToDelete.email} deleted successfully.`);
		await refreshAll();
		deleteDialog.open = false;
	}
</script>

<div class="mb-4 flex justify-end">
	<Button onclick={() => (createDialog.open = true)}>
		<UserPlus class="mr-2 size-4" />Add User
	</Button>
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
<Dialog.Root
	onOpenChange={(open) => {
		editDialog.open = open;
		if (!open) selectedUser = null;
	}}
	open={editDialog.open}
>
	<Dialog.Content class="w-full max-w-[600px] rounded-lg p-6 shadow-lg">
		<Dialog.Header>
			<Dialog.Title class="mb-1 text-xl font-semibold">Edit user</Dialog.Title>
			<Dialog.Description class="mb-4 text-sm">
				Edit {selectedUser?.email}
			</Dialog.Description>
		</Dialog.Header>
		{#if selectedUser}
			<div class="space-y-6">
				<InlineEditField
					id="edit-display-name"
					label="Display Name"
					onSave={saveDisplayName}
					value={selectedUser.display_name ?? ''}
				/>
				<InlineEditField
					id="edit-email"
					label="Email"
					onSave={saveEmail}
					type="email"
					value={selectedUser.email}
				/>
				{#if passwordLoginEnabled}
					<div>
						<span class="mb-1 block text-sm font-medium">Password</span>
						<ChangePasswordDialog userId={selectedUser.id} />
					</div>
				{/if}
				<hr />
				<ToggleField
					checked={selectedUser.is_verified}
					description="New users that created their own account need to be verified before they can sign in and use the app."
					id="verified"
					label="Verified"
					onCheckedChange={(checked) => saveToggle('is_verified', checked)}
				/>
				<ToggleField
					checked={selectedUser.is_active}
					description="Deactivate a user account to block access without deleting the account."
					id="active"
					label="Active"
					onCheckedChange={(checked) => saveToggle('is_active', checked)}
				/>
				<ToggleField
					checked={selectedUser.is_superuser}
					description="Admins can manage users and access all administrative settings."
					id="superuser"
					label="Admin"
					onCheckedChange={(checked) => saveToggle('is_superuser', checked)}
				/>
			</div>
		{/if}
		<div class="mt-8 flex justify-end gap-2">
			<Button onclick={() => (editDialog.open = false)} variant="outline">
				<X class="mr-2 size-4" />Close
			</Button>
		</div>
	</Dialog.Content>
</Dialog.Root>
<AlertDialog.Root bind:open={() => deleteDialog.open, (v) => (deleteDialog.open = v)}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Delete User</AlertDialog.Title>
			<AlertDialog.Description>
				Are you sure you want to delete the user <strong>{userToDelete?.email}</strong>? This action
				cannot be undone.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel disabled={isDeleting} onclick={() => (deleteDialog.open = false)}>
				<X class="mr-2 size-4" />Cancel</AlertDialog.Cancel
			>
			<AlertDialog.Action
				disabled={isDeleting}
				onclick={() => deleteUser()}
				class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
				><Trash2 class="mr-2 size-4" />{isDeleting ? 'Deleting…' : 'Delete'}</AlertDialog.Action
			>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
<Dialog.Root open={createDialog.open} onOpenChange={(open) => (createDialog.open = open)}>
	<Dialog.Content class="w-full max-w-[500px] rounded-lg p-6 shadow-lg">
		<Dialog.Header>
			<Dialog.Title class="mb-1 text-xl font-semibold">Add user</Dialog.Title>
			<Dialog.Description class="mb-4 text-sm">Create a new user account.</Dialog.Description>
		</Dialog.Header>
		<div class="space-y-4">
			<div>
				<Label class="mb-1 block text-sm font-medium" for="create-display-name">Display Name</Label>
				<Input
					bind:value={createDisplayName}
					class="w-full"
					id="create-display-name"
					placeholder="Optional"
					type="text"
				/>
			</div>
			<div>
				<Label class="mb-1 block text-sm font-medium" for="create-email">Email</Label>
				<Input
					bind:value={createEmail}
					class="w-full"
					id="create-email"
					placeholder="user@example.com"
					required
					type="email"
				/>
			</div>
			{#if passwordLoginEnabled}
				<div>
					<Label class="mb-1 block text-sm font-medium" for="create-password">Password</Label>
					<Input
						bind:value={createPassword}
						class="w-full"
						id="create-password"
						placeholder="Optional"
						type="password"
					/>
					<p class="mt-1 text-sm text-muted-foreground">
						Leave blank to randomly generate the password. This may be useful when the user will
						only sign in via OIDC.
					</p>
				</div>
			{/if}
			<hr />
			<ToggleField
				checked={createIsSuperuser}
				description="Admins can manage users and access all administrative settings."
				id="create-superuser"
				label="Admin"
				onCheckedChange={(checked) => (createIsSuperuser = checked)}
			/>
		</div>
		<div class="mt-8 flex justify-end gap-2">
			<Button onclick={() => (createDialog.open = false)} variant="outline">
				<X class="mr-2 size-4" />Cancel
			</Button>
			<Button onclick={() => createUser()} disabled={!createEmail || isCreating}>
				<Check class="mr-2 size-4" />{isCreating ? 'Creating…' : 'Create'}
			</Button>
		</div>
	</Dialog.Content>
</Dialog.Root>
