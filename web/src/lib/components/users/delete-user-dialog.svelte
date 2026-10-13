<script lang="ts">
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import { toast } from 'svelte-sonner';
	import { refreshAll } from '$app/navigation';
	import { shallowDialogsSettled } from '$lib/hooks/shallow-dialog.svelte';
	import client from '$lib/api';
	import type { UserRead } from '$lib/api/api';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import X from '@lucide/svelte/icons/x';

	let {
		user,
		open = $bindable(),
		onDeleted
	}: { user: UserRead | null; open: boolean; onDeleted?: () => void } = $props();

	let isDeleting = $state(false);
	// Unverified users are pending sign-ups that can't have used the app yet,
	// so deleting one is framed as rejecting the sign-up.
	let isPending = $derived(user ? !user.is_verified : false);
	let actionLabel = $derived(
		isPending ? (isDeleting ? 'Rejecting…' : 'Reject') : isDeleting ? 'Deleting…' : 'Delete'
	);

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
			toast.error(`Failed to delete user ${user.email}: ${error.detail}`);
			isDeleting = false;
			return;
		}
		toast.success(
			isPending ? `Sign-up of ${user.email} rejected.` : `User ${user.email} deleted successfully.`
		);
		open = false;
		onDeleted?.();
		await shallowDialogsSettled();
		await refreshAll();
	}
</script>

<AlertDialog.Root bind:open>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>{isPending ? 'Reject Sign-up' : 'Delete User'}</AlertDialog.Title>
			<AlertDialog.Description>
				{#if isPending}
					Are you sure you want to reject the sign-up of <strong>{user?.email}</strong>? Their
					account will be deleted. They can sign up again later.
				{:else}
					<div class="space-y-2">
						<p>
							Are you sure you want to permanently delete the user <strong>{user?.email}</strong>?
							<strong>This action is irreversible.</strong>
						</p>
						<ul class="list-disc space-y-1 pl-5">
							<li>Their user page will be removed.</li>
							<li>
								Shows, movies and downloads they added will no longer be attributed to anyone.
							</li>
							<li>Links and references to this user elsewhere in the app will stop working.</li>
						</ul>
						<p>If you only want to block access, keep the user deactivated instead.</p>
					</div>
				{/if}
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
				<Trash2 class="mr-2 size-4" />{actionLabel}
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
