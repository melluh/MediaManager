<script lang="ts">
	import { Button, buttonVariants } from '$lib/components/ui/button/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import UserRoleBadge from '$lib/components/users/user-role-badge.svelte';
	import UserStatusBadge from '$lib/components/users/user-status-badge.svelte';
	import UserPill from '$lib/components/user-pill.svelte';
	import InlineEditField from '$lib/components/inline-edit-field.svelte';
	import ChangePasswordDialog from '$lib/components/change-password-dialog.svelte';
	import DeleteUserDialog from '$lib/components/users/delete-user-dialog.svelte';
	import DeactivateUserDialog from '$lib/components/users/deactivate-user-dialog.svelte';
	import { toast } from 'svelte-sonner';
	import { refreshAll } from '$app/navigation';
	import client from '$lib/api';
	import type { OAuthAccountRead, UserRead, UserUpdate } from '$lib/api/api';
	import X from '@lucide/svelte/icons/x';
	import UserCheck from '@lucide/svelte/icons/user-check';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import UserX from '@lucide/svelte/icons/user-x';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import ShieldOff from '@lucide/svelte/icons/shield-off';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Info from '@lucide/svelte/icons/info';
	import UnlinkOAuthAccountDialog from '$lib/components/users/unlink-oauth-account-dialog.svelte';
	import MediaServerAccountPicker from '$lib/components/users/media-server-account-picker.svelte';
	import { meta } from '$lib/hooks/meta.svelte.js';

	let {
		user = $bindable(),
		open = $bindable(),
		passwordLoginEnabled,
		isSelf = false
	}: {
		user: UserRead | null;
		open: boolean;
		passwordLoginEnabled: boolean;
		// Hides the actions that would lock the admin out of their own account.
		isSelf?: boolean;
	} = $props();

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

	let isChangingAdmin = $state(false);

	async function setAdmin(isSuperuser: boolean) {
		if (!user || isChangingAdmin) return;
		isChangingAdmin = true;
		const ok = await patchUser({ is_superuser: isSuperuser });
		isChangingAdmin = false;
		if (!ok) {
			toast.error(`Failed to ${isSuperuser ? 'promote' : 'demote'} user ${user.email}`);
			return;
		}
		user.is_superuser = isSuperuser;
		toast.success(
			isSuperuser
				? `User ${user.email} promoted to admin.`
				: `User ${user.email} is no longer an admin.`
		);
		await refreshAll();
	}

	let isReactivating = $state(false);
	let deleteDialogOpen = $state(false);
	let deactivateDialogOpen = $state(false);
	let unlinkDialogOpen = $state(false);
	let accountToUnlink: OAuthAccountRead | null = $state(null);

	async function reactivate() {
		if (!user || isReactivating) return;
		isReactivating = true;
		const ok = await patchUser({ is_active: true });
		isReactivating = false;
		if (!ok) {
			toast.error(`Failed to reactivate user ${user.email}`);
			return;
		}
		user.is_active = true;
		toast.success(`User ${user.email} reactivated.`);
		await refreshAll();
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="w-full max-w-[600px] rounded-lg p-6 shadow-lg" showCloseButton={false}>
		<div class="flex items-start justify-between gap-4">
			<Dialog.Header>
				<Dialog.Title class="mb-1 text-xl font-semibold">Editing user</Dialog.Title>
				<Dialog.Description class="mb-4 flex flex-wrap items-center gap-2 text-sm">
					{#if user}
						<UserPill
							userId={user.id}
							name={user.display_name || user.email}
							isAdmin={user.is_superuser}
						/>
						<UserStatusBadge {user} />
						{#if user.is_superuser}
							<UserRoleBadge {user} />
						{/if}
					{/if}
				</Dialog.Description>
			</Dialog.Header>
			<div class="flex shrink-0 items-center gap-2">
				{#if user && !isSelf}
					<DropdownMenu.Root>
						<DropdownMenu.Trigger class={buttonVariants({ variant: 'outline', size: 'sm' })}>
							Actions<ChevronDown class="ml-1 size-4" />
						</DropdownMenu.Trigger>
						<DropdownMenu.Content align="end" class="w-48">
							{#if user.is_superuser}
								<DropdownMenu.Item disabled={isChangingAdmin} onclick={() => setAdmin(false)}>
									<ShieldOff />
									Demote from admin
								</DropdownMenu.Item>
							{:else}
								<DropdownMenu.Item disabled={isChangingAdmin} onclick={() => setAdmin(true)}>
									<ShieldCheck />
									Promote to admin
								</DropdownMenu.Item>
							{/if}
							{#if user.is_active}
								<DropdownMenu.Separator />
								<DropdownMenu.Item
									onclick={() => (deactivateDialogOpen = true)}
									class="text-destructive data-[highlighted]:bg-destructive/10 data-[highlighted]:text-destructive"
								>
									<UserX />
									Deactivate
								</DropdownMenu.Item>
							{:else}
								<DropdownMenu.Item disabled={isReactivating} onclick={reactivate}>
									<UserCheck />
									Reactivate
								</DropdownMenu.Item>
								<DropdownMenu.Separator />
								<DropdownMenu.Item
									onclick={() => (deleteDialogOpen = true)}
									class="text-destructive data-[highlighted]:bg-destructive/10 data-[highlighted]:text-destructive"
								>
									<Trash2 />
									Delete permanently
								</DropdownMenu.Item>
							{/if}
						</DropdownMenu.Content>
					</DropdownMenu.Root>
				{/if}
				<Dialog.Close class={buttonVariants({ variant: 'ghost', size: 'icon', class: 'size-8' })}>
					<X class="size-4" />
					<span class="sr-only">Close</span>
				</Dialog.Close>
			</div>
		</div>
		{#if user}
			{#if isSelf}
				<Alert.Root class="mb-4 flex items-center gap-3">
					<Info class="size-4 shrink-0" />
					<Alert.Description
						><strong>This is your own account. </strong> You can edit the account details, but you can't
						demote, deactivate, or delete your own account.</Alert.Description
					>
				</Alert.Root>
			{/if}
			<div class="space-y-2">
				<InlineEditField
					horizontal
					id="edit-display-name"
					label="Display Name"
					onSave={saveDisplayName}
					value={user.display_name ?? ''}
				/>
				<InlineEditField
					horizontal
					id="edit-email"
					label="Email"
					onSave={saveEmail}
					type="email"
					value={user.email}
				/>
				{#if meta.current?.media_server}
					<div class="grid min-h-9 grid-cols-[8rem_1fr] items-center gap-4">
						<span class="text-sm font-medium text-muted-foreground">
							{meta.current.media_server.display_name} Account
						</span>
						<MediaServerAccountPicker bind:user mediaServer={meta.current.media_server} />
					</div>
				{/if}
				<div class="grid min-h-9 grid-cols-[8rem_1fr] items-center gap-4">
					<span class="text-sm font-medium text-muted-foreground">Linked Accounts</span>
					{#if user.oauth_accounts?.length}
						<div class="flex flex-wrap gap-2">
							{#each user.oauth_accounts as account (account.id)}
								<div
									class="flex h-9 items-center gap-2 rounded-md border pr-1 pl-3 text-sm font-medium"
								>
									<span>{account.oauth_name}: {account.account_email}</span>
									<Button
										variant="ghost"
										size="icon"
										class="size-7 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
										onclick={() => {
											accountToUnlink = account;
											unlinkDialogOpen = true;
										}}
									>
										<Trash2 class="size-4" />
										<span class="sr-only">Unlink {account.oauth_name} account</span>
									</Button>
								</div>
							{/each}
						</div>
					{:else}
						<p class="text-sm text-muted-foreground">No linked OAuth accounts.</p>
					{/if}
				</div>
				{#if passwordLoginEnabled}
					<div class="grid grid-cols-[8rem_1fr] items-center gap-4">
						<span class="text-sm font-medium text-muted-foreground">Password</span>
						<div><ChangePasswordDialog userId={user.id} /></div>
					</div>
				{/if}
			</div>
		{/if}
	</Dialog.Content>
</Dialog.Root>
<DeactivateUserDialog
	{user}
	bind:open={deactivateDialogOpen}
	onDeactivated={() => {
		if (user) user.is_active = false;
	}}
/>
<UnlinkOAuthAccountDialog
	{user}
	account={accountToUnlink}
	bind:open={unlinkDialogOpen}
	onUnlinked={() => {
		if (user)
			user.oauth_accounts = user.oauth_accounts?.filter((a) => a.id !== accountToUnlink?.id);
	}}
/>
<DeleteUserDialog {user} bind:open={deleteDialogOpen} onDeleted={() => (open = false)} />
