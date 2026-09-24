<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import InlineEditField from '$lib/components/inline-edit-field.svelte';
	import ToggleField from '$lib/components/toggle-field.svelte';
	import ChangePasswordDialog from '$lib/components/change-password-dialog.svelte';
	import { toast } from 'svelte-sonner';
	import { refreshAll } from '$app/navigation';
	import client from '$lib/api';
	import type { UserRead, UserUpdate } from '$lib/api/api';
	import X from '@lucide/svelte/icons/x';

	let {
		user = $bindable(),
		open = $bindable(),
		passwordLoginEnabled
	}: { user: UserRead | null; open: boolean; passwordLoginEnabled: boolean } = $props();

	async function patchUser(body: UserUpdate): Promise<boolean> {
		if (!user) return false;
		const { error } = await client.PATCH('/api/v1/users/{id}', {
			params: { path: { id: user.id } },
			body
		});
		return !error;
	}

	async function saveDisplayName(newDisplayName: string): Promise<boolean> {
		if (!user || !(await patchUser({ display_name: newDisplayName }))) {
			toast.error('Failed to update display name');
			return false;
		}
		toast.success('Display name updated successfully.');
		user.display_name = newDisplayName;
		await refreshAll();
		return true;
	}

	async function saveEmail(newEmail: string): Promise<boolean> {
		if (!user || !(await patchUser({ email: newEmail }))) {
			toast.error('Failed to update email');
			return false;
		}
		toast.success('Email updated successfully.');
		user.email = newEmail;
		await refreshAll();
		return true;
	}

	async function saveToggle(field: 'is_verified' | 'is_active' | 'is_superuser', value: boolean) {
		if (!user) return;
		const previousValue = user[field];
		user[field] = value;
		if (!(await patchUser({ [field]: value }))) {
			user[field] = previousValue;
			toast.error(`Failed to update user ${user.email}`);
			return;
		}
		toast.success(`User ${user.email} updated successfully.`);
		await refreshAll();
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="w-full max-w-[600px] rounded-lg p-6 shadow-lg">
		<Dialog.Header>
			<Dialog.Title class="mb-1 text-xl font-semibold">Edit user</Dialog.Title>
			<Dialog.Description class="mb-4 text-sm">
				Edit {user?.email}
			</Dialog.Description>
		</Dialog.Header>
		{#if user}
			<div class="space-y-6">
				<InlineEditField
					id="edit-display-name"
					label="Display Name"
					onSave={saveDisplayName}
					value={user.display_name ?? ''}
				/>
				<InlineEditField
					id="edit-email"
					label="Email"
					onSave={saveEmail}
					type="email"
					value={user.email}
				/>
				{#if passwordLoginEnabled}
					<div>
						<span class="mb-1 block text-sm font-medium">Password</span>
						<ChangePasswordDialog userId={user.id} />
					</div>
				{/if}
				<hr />
				<ToggleField
					checked={user.is_verified}
					description="New users that created their own account need to be verified before they can sign in and use the app."
					id="verified"
					label="Verified"
					onCheckedChange={(checked) => saveToggle('is_verified', checked)}
				/>
				<ToggleField
					checked={user.is_active}
					description="Deactivate a user account to block access without deleting the account."
					id="active"
					label="Active"
					onCheckedChange={(checked) => saveToggle('is_active', checked)}
				/>
				<ToggleField
					checked={user.is_superuser}
					description="Admins can manage users and access all administrative settings."
					id="superuser"
					label="Admin"
					onCheckedChange={(checked) => saveToggle('is_superuser', checked)}
				/>
			</div>
		{/if}
		<div class="mt-8 flex justify-end gap-2">
			<Button onclick={() => (open = false)} variant="outline">
				<X class="mr-2 size-4" />Close
			</Button>
		</div>
	</Dialog.Content>
</Dialog.Root>
