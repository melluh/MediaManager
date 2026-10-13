<script lang="ts">
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import { toast } from 'svelte-sonner';
	import { refreshAll } from '$app/navigation';
	import client from '$lib/api';
	import type { UserRead } from '$lib/api/api';
	import UserX from '@lucide/svelte/icons/user-x';
	import X from '@lucide/svelte/icons/x';

	let {
		user,
		open = $bindable(),
		onDeactivated
	}: { user: UserRead | null; open: boolean; onDeactivated?: () => void } = $props();

	let isDeactivating = $state(false);

	// Reset once the (asynchronously closing) dialog is actually gone, so the
	// loading state stays visible until then.
	$effect(() => {
		if (!open) isDeactivating = false;
	});

	async function deactivateUser() {
		if (!user || isDeactivating) return;
		isDeactivating = true;

		const { error } = await client.PATCH('/api/v1/users/{id}', {
			params: { path: { id: user.id } },
			body: { is_active: false }
		});

		if (error) {
			toast.error(`Failed to deactivate user ${user.email}`);
			isDeactivating = false;
			return;
		}
		toast.success(`User ${user.email} deactivated.`);
		open = false;
		onDeactivated?.();
		await refreshAll();
	}
</script>

<AlertDialog.Root bind:open>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Deactivate User</AlertDialog.Title>
			<AlertDialog.Description>
				Are you sure you want to deactivate the user <strong>{user?.email}</strong>? They will no
				longer be able to sign in or use the app. You can reactivate them at any time.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel disabled={isDeactivating} onclick={() => (open = false)}>
				<X class="mr-2 size-4" />Cancel
			</AlertDialog.Cancel>
			<AlertDialog.Action
				disabled={isDeactivating}
				onclick={deactivateUser}
				class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
			>
				<UserX class="mr-2 size-4" />{isDeactivating ? 'Deactivating…' : 'Deactivate'}
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
