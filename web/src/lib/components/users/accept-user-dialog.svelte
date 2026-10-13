<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { toast } from 'svelte-sonner';
	import { refreshAll } from '$app/navigation';
	import client from '$lib/api';
	import type { UserRead } from '$lib/api/api';
	import Check from '@lucide/svelte/icons/check';
	import X from '@lucide/svelte/icons/x';

	let { user, open = $bindable() }: { user: UserRead | null; open: boolean } = $props();

	let displayName = $state('');
	let isAccepting = $state(false);

	// Reset once the (asynchronously closing) dialog is actually gone, so the
	// loading state stays visible until then.
	$effect(() => {
		if (!open) {
			displayName = '';
			isAccepting = false;
		}
	});

	async function acceptUser(event: SubmitEvent) {
		event.preventDefault();
		if (!user || isAccepting) return;
		isAccepting = true;
		const { error } = await client.PATCH('/api/v1/users/{id}', {
			params: { path: { id: user.id } },
			body: { is_verified: true, ...(displayName.trim() && { display_name: displayName.trim() }) }
		});
		if (error) {
			toast.error(`Failed to accept user ${user.email}`);
			isAccepting = false;
			return;
		}
		toast.success(`User ${user.email} accepted.`);
		await refreshAll();
		open = false;
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="w-full max-w-[500px] rounded-lg p-6 shadow-lg">
		<form onsubmit={acceptUser}>
			<Dialog.Header>
				<Dialog.Title class="mb-1 text-xl font-semibold">Accept sign-up</Dialog.Title>
				<Dialog.Description class="mb-4 text-sm">
					Are you sure you want to accept <strong>{user?.email}</strong>? They will be able to sign
					in and use the app.
				</Dialog.Description>
			</Dialog.Header>
			<div>
				<Label class="mb-1 block text-sm font-medium" for="accept-display-name">
					Set a display name for this user?
					<span class="font-normal text-muted-foreground">(optional)</span>
				</Label>
				<Input
					bind:value={displayName}
					class="w-full"
					id="accept-display-name"
					placeholder={user?.email ?? ''}
					type="text"
				/>
			</div>
			<div class="mt-8 flex justify-end gap-2">
				<Button onclick={() => (open = false)} type="button" variant="outline">
					<X class="mr-2 size-4" />Cancel
				</Button>
				<Button disabled={isAccepting} type="submit">
					<Check class="mr-2 size-4" />{isAccepting ? 'Accepting…' : 'Accept'}
				</Button>
			</div>
		</form>
	</Dialog.Content>
</Dialog.Root>
