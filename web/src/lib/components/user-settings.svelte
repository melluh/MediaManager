<script lang="ts">
	import { toast } from 'svelte-sonner';
	import client from '$lib/api';
	import { invalidateAll } from '$app/navigation';
	import { getContext } from 'svelte';
	import type { UserReadWithPermissions } from '$lib/api/api';
	import InlineEditField from '$lib/components/inline-edit-field.svelte';
	import ChangePasswordDialog from '$lib/components/change-password-dialog.svelte';
	import { Badge } from '$lib/components/ui/badge';

	let { passwordLoginEnabled = true }: { passwordLoginEnabled?: boolean } = $props();

	let currentUser: () => UserReadWithPermissions = getContext('user');

	let canEditAccount = $derived(currentUser().permissions.can_edit_account);
	let canChangePassword = $derived(currentUser().permissions.can_change_password);
	let oauthAccounts = $derived(currentUser().oauth_accounts ?? []);

	const disabledEditMessage =
		"You can't edit your own account details. Contact a superuser for assistance.";

	async function saveDisplayName(newDisplayName: string): Promise<boolean> {
		const { error } = await client.PATCH('/api/v1/users/me', {
			body: { display_name: newDisplayName }
		});
		if (error) {
			toast.error('Failed to update display name');
			return false;
		}
		toast.success('Display name updated successfully.');
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
		id="display-name"
		label="Display Name"
		onSave={saveDisplayName}
		value={currentUser().display_name ?? ''}
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
	{#if passwordLoginEnabled}
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
	{/if}
	<div>
		<span class="mb-1 block text-sm font-medium">Linked Accounts</span>
		{#if oauthAccounts.length > 0}
			<div class="flex flex-wrap gap-2">
				{#each oauthAccounts as account (account.id)}
					<Badge variant="outline">{account.oauth_name}: {account.account_email}</Badge>
				{/each}
			</div>
		{:else}
			<p class="text-sm text-muted-foreground">No OAuth accounts are linked to your account.</p>
		{/if}
	</div>
</div>
