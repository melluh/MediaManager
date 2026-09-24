<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import ToggleField from '$lib/components/toggle-field.svelte';
	import { toast } from 'svelte-sonner';
	import { refreshAll } from '$app/navigation';
	import client from '$lib/api';
	import UserPlus from '@lucide/svelte/icons/user-plus';
	import X from '@lucide/svelte/icons/x';
	import Check from '@lucide/svelte/icons/check';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';

	let { passwordLoginEnabled }: { passwordLoginEnabled: boolean } = $props();

	const dialog = shallowDialog('createUser');
	let email = $state('');
	let displayName = $state('');
	let password = $state('');
	let isSuperuser = $state(false);
	let isCreating = $state(false);

	// Closing a shallow-routed dialog goes through an async history.back(), and it can be
	// closed from several places (Cancel, Escape, an overlay click, or a successful
	// submit), so cleanup is centralized here rather than duplicated at each call site.
	// This also keeps the loading state visible for the whole time the dialog is still
	// on screen, instead of flipping back to normal before it closes.
	$effect(() => {
		if (!dialog.open) {
			email = '';
			displayName = '';
			password = '';
			isSuperuser = false;
			isCreating = false;
		}
	});

	async function createUser() {
		if (isCreating) return;
		isCreating = true;
		const { error } = await client.POST('/api/v1/users/', {
			body: {
				email,
				display_name: displayName || null,
				password: password || null,
				is_superuser: isSuperuser,
				is_verified: true
			}
		});
		if (error) {
			toast.error(`Failed to create user: ${error.detail ?? error}`);
			isCreating = false;
			return;
		}
		toast.success(`User ${email} created successfully.`);
		await refreshAll();
		dialog.open = false;
	}
</script>

<Button onclick={() => (dialog.open = true)}>
	<UserPlus class="mr-2 size-4" />Add User
</Button>
<Dialog.Root bind:open={dialog.open}>
	<Dialog.Content class="w-full max-w-[500px] rounded-lg p-6 shadow-lg">
		<Dialog.Header>
			<Dialog.Title class="mb-1 text-xl font-semibold">Add user</Dialog.Title>
			<Dialog.Description class="mb-4 text-sm">Create a new user account.</Dialog.Description>
		</Dialog.Header>
		<div class="space-y-4">
			<div>
				<Label class="mb-1 block text-sm font-medium" for="create-display-name">Display Name</Label>
				<Input
					bind:value={displayName}
					class="w-full"
					id="create-display-name"
					placeholder="Optional"
					type="text"
				/>
			</div>
			<div>
				<Label class="mb-1 block text-sm font-medium" for="create-email">Email</Label>
				<Input
					bind:value={email}
					class="w-full"
					id="create-email"
					placeholder="user@example.com"
					required
					type="email"
				/>
			</div>
			{#if passwordLoginEnabled}
				<div>
					<Label class="mb-1 block text-sm font-medium" for="create-password">Password</Label>
					<Input
						bind:value={password}
						class="w-full"
						id="create-password"
						placeholder="Optional"
						type="password"
					/>
					<p class="mt-1 text-sm text-muted-foreground">
						Leave blank to randomly generate the password. This may be useful when the user will
						only sign in via OIDC.
					</p>
				</div>
			{/if}
			<hr />
			<ToggleField
				checked={isSuperuser}
				description="Admins can manage users and access all administrative settings."
				id="create-superuser"
				label="Admin"
				onCheckedChange={(checked) => (isSuperuser = checked)}
			/>
		</div>
		<div class="mt-8 flex justify-end gap-2">
			<Button onclick={() => (dialog.open = false)} variant="outline">
				<X class="mr-2 size-4" />Cancel
			</Button>
			<Button onclick={createUser} disabled={!email || isCreating}>
				<Check class="mr-2 size-4" />{isCreating ? 'Creating…' : 'Create'}
			</Button>
		</div>
	</Dialog.Content>
</Dialog.Root>
