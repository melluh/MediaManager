<script lang="ts">
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import { toast } from 'svelte-sonner';
	import { refreshAll } from '$app/navigation';
	import client from '$lib/api';
	import type { UserRead } from '$lib/api/api';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import X from '@lucide/svelte/icons/x';

	let { user, open = $bindable() }: { user: UserRead | null; open: boolean } = $props();

	let isDeleting = $state(false);

	// Reset once the (asynchronously closing) dialog is actually gone, so the
	// loading state stays visible until then.
	$effect(() => {
		if (!open) isDeleting = false;
	});

	async function deleteUser() {
		if (!user || isDeleting) return;
		isDeleting = true;

		const { error } = await client.DELETE('/api/v1/users/{id}', {
			params: { path: { id: user.id } }
		});

		if (error) {
			toast.error(`Failed to delete user ${user.email}: ${error}`);
			isDeleting = false;
			return;
		}
		toast.success(`User ${user.email} deleted successfully.`);
		await refreshAll();
		open = false;
	}
</script>

<AlertDialog.Root bind:open>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Delete User</AlertDialog.Title>
			<AlertDialog.Description>
				Are you sure you want to delete the user <strong>{user?.email}</strong>? This action cannot
				be undone.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel disabled={isDeleting} onclick={() => (open = false)}>
				<X class="mr-2 size-4" />Cancel
			</AlertDialog.Cancel>
			<AlertDialog.Action
				disabled={isDeleting}
				onclick={deleteUser}
				class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
			>
				<Trash2 class="mr-2 size-4" />{isDeleting ? 'Deleting…' : 'Delete'}
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
