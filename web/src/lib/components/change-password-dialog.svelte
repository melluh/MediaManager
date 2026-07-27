<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import { toast } from 'svelte-sonner';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import client from '$lib/api';

	let newPassword: string = $state('');
	let dialogOpen = $state(false);

	function closeDialog() {
		dialogOpen = false;
		newPassword = '';
	}

	async function savePassword() {
		const { error } = await client.PATCH('/api/v1/users/me', {
			body: {
				password: newPassword
			}
		});
		if (error) {
			toast.error('Failed to update password');
			return;
		}
		toast.success('Password updated successfully.');
		closeDialog();
	}
</script>

<Dialog.Root bind:open={dialogOpen}>
	<Dialog.Trigger>
		<Button onclick={() => (dialogOpen = true)} variant="outline">Change Password</Button>
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
			<Button onclick={closeDialog} variant="secondary">Cancel</Button>
			<Button disabled={newPassword === ''} onclick={savePassword}>Save</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
