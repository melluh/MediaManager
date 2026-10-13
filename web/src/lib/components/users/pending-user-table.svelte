<script lang="ts">
	import * as Table from '$lib/components/ui/table/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import DeleteUserDialog from '$lib/components/users/delete-user-dialog.svelte';
	import AcceptUserDialog from '$lib/components/users/accept-user-dialog.svelte';
	import type { UserRead } from '$lib/api/api';
	import Check from '@lucide/svelte/icons/check';
	import X from '@lucide/svelte/icons/x';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';

	let { users }: { users: UserRead[] } = $props();

	let userToReject: UserRead | null = $state(null);
	let userToAccept: UserRead | null = $state(null);
	const rejectDialog = shallowDialog('rejectUser');
	const acceptDialog = shallowDialog('acceptUser');
</script>

<Table.Root>
	<Table.Header>
		<Table.Row>
			<Table.Head>Email</Table.Head>
			<Table.Head></Table.Head>
		</Table.Row>
	</Table.Header>
	<Table.Body>
		{#each users as user (user.id)}
			<Table.Row>
				<Table.Cell>
					<div class="flex items-center gap-2">
						<span>{user.email}</span>
						<Tooltip.Root>
							<Tooltip.Trigger>
								{#snippet child({ props })}
									<Badge {...props} variant="outline" class="cursor-help">Unverified</Badge>
								{/snippet}
							</Tooltip.Trigger>
							<Tooltip.Content class="max-w-xs">
								This is the email address entered at sign-up. It hasn't been confirmed in any way,
								so make sure you recognise this person before accepting.
							</Tooltip.Content>
						</Tooltip.Root>
					</div>
				</Table.Cell>
				<Table.Cell>
					<div class="flex justify-end gap-2">
						<Button
							onclick={() => {
								userToAccept = user;
								acceptDialog.open = true;
							}}
						>
							<Check class="mr-2 size-4" />Accept
						</Button>
						<Button
							variant="destructive"
							onclick={() => {
								userToReject = user;
								rejectDialog.open = true;
							}}
						>
							<X class="mr-2 size-4" />Reject
						</Button>
					</div>
				</Table.Cell>
			</Table.Row>
		{/each}
	</Table.Body>
</Table.Root>
<DeleteUserDialog user={userToReject} bind:open={rejectDialog.open} />
<AcceptUserDialog user={userToAccept} bind:open={acceptDialog.open} />
