<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import { toast } from 'svelte-sonner';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import client from '$lib/api';
	import KeyRound from '@lucide/svelte/icons/key-round';
	import Check from '@lucide/svelte/icons/check';
	import X from '@lucide/svelte/icons/x';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';

	let { userId }: { userId?: string } = $props();

	let newPassword: string = $state('');
	const dialogState = shallowDialog('changePassword');

	function closeDialog() {
		dialogState.open = false;
		newPassword = '';
	}

	async function savePassword() {
		const { error } = userId
			? await client.PATCH('/api/v1/users/{id}', {
					params: { path: { id: userId } },
					body: { password: newPassword }
				})
			: await client.PATCH('/api/v1/users/me', {
					body: { password: newPassword }
				});
		if (error) {
			toast.error('Failed to update password');
			return;
		}
		toast.success('Password updated successfully.');
		closeDialog();
	}
</script>

<Dialog.Root bind:open={() => dialogState.open, (v) => (dialogState.open = v)}>
	<Dialog.Trigger>
		<Button onclick={() => (dialogState.open = true)} variant="outline">
			<KeyRound class="mr-2 size-4" />Change Password
		</Button>
	</Dialog.Trigger>
	<Dialog.Content class="w-full max-w-[600px] rounded-lg p-6 shadow-lg">
		<Dialog.Header>
			<Dialog.Title class="mb-1 text-xl font-semibold">Change Password</Dialog.Title>
			<Dialog.Description class="mb-4 text-sm">Enter a new password.</Dialog.Description>
		</Dialog.Header>
		<div>
			<Label class="mb-1 block text-sm font-medium" for="new-password">New Password</Label>
			<Input
				bind:value={newPassword}
				class="w-full"
				id="new-password"
				onkeydown={(e) => {
					if (e.key === 'Enter' && newPassword !== '') {
						e.preventDefault();
						savePassword();
					}
				}}
				placeholder="New password"
				type="password"
			/>
		</div>
		<Dialog.Footer class="mt-8 flex justify-between gap-2">
			<Button onclick={closeDialog} variant="secondary"><X class="mr-2 size-4" />Cancel</Button>
			<Button disabled={newPassword === ''} onclick={savePassword}>
				<Check class="mr-2 size-4" />Save
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
