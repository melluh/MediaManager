<script lang="ts">
	import { toast } from 'svelte-sonner';
	import client from '$lib/api';
	import { invalidateAll } from '$app/navigation';
	import { getContext } from 'svelte';
	import type { AuthMetadata, UserRead } from '$lib/api/api';
	import InlineEditField from '$lib/components/inline-edit-field.svelte';
	import ChangePasswordDialog from '$lib/components/change-password-dialog.svelte';

	let { authMetadata }: { authMetadata: AuthMetadata } = $props();

	let currentUser: () => UserRead = getContext('user');

	let canEditAccount = $derived(currentUser().is_superuser || authMetadata.allow_self_account_edit);
	let canChangePassword = $derived(
		currentUser().is_superuser || authMetadata.allow_self_password_change
	);

	const disabledEditMessage =
		"You can't edit your own account details. Contact a superuser for assistance.";

	async function saveUsername(newUsername: string): Promise<boolean> {
		const { error } = await client.PATCH('/api/v1/users/me', {
			body: { username: newUsername }
		});
		if (error) {
			toast.error('Failed to update username');
			return false;
		}
		toast.success('Username updated successfully.');
		await invalidateAll();
		return true;
	}

	async function saveEmail(newEmail: string): Promise<boolean> {
		const { error } = await client.PATCH('/api/v1/users/me', {
			body: { email: newEmail }
		});
		if (error) {
			toast.error('Failed to update email');
			return false;
		}
		toast.success('Email updated successfully.');
		await invalidateAll();
		return true;
	}
</script>

<div class="space-y-6">
	<InlineEditField
		id="username"
		label="Username"
		onSave={saveUsername}
		value={currentUser().username ?? ''}
		editable={canEditAccount}
		disabledMessage={disabledEditMessage}
	/>
	<InlineEditField
		id="email"
		label="Email"
		onSave={saveEmail}
		type="email"
		value={currentUser().email}
		editable={canEditAccount}
		disabledMessage={disabledEditMessage}
	/>
	<div>
		<span class="mb-1 block text-sm font-medium">Password</span>
		{#if canChangePassword}
			<ChangePasswordDialog />
		{:else}
			<p class="text-sm text-muted-foreground">
				You can't change your own password. Contact a superuser for assistance.
			</p>
		{/if}
	</div>
</div>
