<script lang="ts">
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import { toast } from 'svelte-sonner';
	import { refreshAll } from '$app/navigation';
	import client from '$lib/api';
	import type { OAuthAccountRead, UserRead } from '$lib/api/api';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import X from '@lucide/svelte/icons/x';
	import Info from '@lucide/svelte/icons/info';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';

	let {
		user,
		account,
		open = $bindable(),
		onUnlinked
	}: {
		user: UserRead | null;
		account: OAuthAccountRead | null;
		open: boolean;
		onUnlinked?: () => void;
	} = $props();

	let isUnlinking = $state(false);
	// Logins are matched to a linked account first and only fall back to the
	// email address when none is linked. So unlinking an account whose email
	// matches the user just gets it linked again on the next login.
	let emailsMatch = $derived(
		!!user && !!account && user.email.toLowerCase() === account.account_email.toLowerCase()
	);

	// Reset when the dialog opens rather than when it closes, so the loading
	// state stays visible during the close animation.
	$effect(() => {
		if (open) isUnlinking = false;
	});

	async function unlink() {
		if (!user || !account || isUnlinking) return;
		isUnlinking = true;

		const { error } = await client.DELETE(
			'/api/v1/users/{user_id}/oauth-accounts/{oauth_account_id}',
			{ params: { path: { user_id: user.id, oauth_account_id: account.id } } }
		);

		if (error) {
			toast.error(`Failed to unlink ${account.oauth_name} account: ${error.detail}`);
			isUnlinking = false;
			return;
		}
		toast.success(`${account.oauth_name} account ${account.account_email} unlinked.`);
		open = false;
		onUnlinked?.();
		await refreshAll();
	}
</script>

<AlertDialog.Root bind:open>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Unlink Account</AlertDialog.Title>
			<AlertDialog.Description>
				Are you sure you want to unlink the {account?.oauth_name} account
				<strong>{account?.account_email}</strong> from <strong>{user?.email}</strong>?
			</AlertDialog.Description>
		</AlertDialog.Header>
		{#if emailsMatch}
			<div
				class="flex items-start gap-2 rounded-md border border-amber-500/50 bg-amber-500/10 p-3 text-sm"
			>
				<TriangleAlert class="mt-0.5 size-4 shrink-0 text-amber-500" />
				<div class="space-y-2">
					<p>
						<strong>This will most likely have no lasting effect</strong>, because the user's email
						address matches the {account?.oauth_name} account's email address.
					</p>
					<p>
						The next time they log in with this {account?.oauth_name} account, it will automatically be
						linked to this user again.
					</p>
					<p>To block them from logging in, deactivate the user instead.</p>
				</div>
			</div>
		{:else}
			<div class="flex items-start gap-2 rounded-md border bg-muted/50 p-3 text-sm">
				<Info class="mt-0.5 size-4 shrink-0" />
				<div class="space-y-2">
					<p>
						This {account?.oauth_name} account will be unlinked from this user.
					</p>
					<p>
						If this
						{account?.oauth_name} account is used to log in again, it will be linked to the (possibly
						new) user with the email address <strong>{account?.account_email}</strong>.
					</p>
				</div>
			</div>
		{/if}
		<AlertDialog.Footer>
			<AlertDialog.Cancel disabled={isUnlinking} onclick={() => (open = false)}>
				<X class="mr-2 size-4" />Cancel
			</AlertDialog.Cancel>
			<AlertDialog.Action
				disabled={isUnlinking}
				onclick={unlink}
				class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
			>
				<Trash2 class="mr-2 size-4" />Unlink
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
