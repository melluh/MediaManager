<script lang="ts">
	import { Button, buttonVariants } from '$lib/components/ui/button/index.js';
	import * as Command from '$lib/components/ui/command/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import { toast } from 'svelte-sonner';
	import { refreshAll } from '$app/navigation';
	import client from '$lib/api';
	import type { MediaServerInfo, MediaServerUserOption, UserRead } from '$lib/api/api';
	import { cn } from '$lib/utils.js';
	import Check from '@lucide/svelte/icons/check';
	import ChevronsUpDown from '@lucide/svelte/icons/chevrons-up-down';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import X from '@lucide/svelte/icons/x';

	let { user = $bindable(), mediaServer }: { user: UserRead; mediaServer: MediaServerInfo } =
		$props();

	let linkedAccount = $derived(
		user.media_server_accounts?.find((account) => account.provider === mediaServer.name)
	);

	let open = $state(false);
	let options: MediaServerUserOption[] | null = $state(null);
	let loadError = $state(false);
	let isSaving = $state(false);

	async function loadOptions() {
		loadError = false;
		const { data, error } = await client.GET('/api/v1/media-server/users');
		if (error || !data) {
			loadError = true;
			return;
		}
		options = data;
	}

	$effect(() => {
		// Refetched on every open, so accounts linked or unlinked elsewhere in the
		// meantime show up correctly.
		if (open) {
			options = null;
			loadOptions();
		}
	});

	async function link(option: MediaServerUserOption) {
		open = false;
		if (isSaving || option.id === linkedAccount?.external_user_id) return;
		isSaving = true;
		const { data, error } = await client.PUT('/api/v1/users/{user_id}/media-server-account', {
			params: { path: { user_id: user.id } },
			body: { external_user_id: option.id }
		});
		isSaving = false;
		if (error || !data) {
			toast.error(
				(typeof error?.detail === 'string' && error.detail) ||
					`Failed to link ${mediaServer.display_name} account`
			);
			return;
		}
		user.media_server_accounts = [
			...(user.media_server_accounts ?? []).filter((a) => a.provider !== mediaServer.name),
			data
		];
		toast.success(`Linked ${mediaServer.display_name} account ${data.username}.`);
		await refreshAll();
	}

	async function unlink() {
		if (isSaving) return;
		isSaving = true;
		const { error } = await client.DELETE('/api/v1/users/{user_id}/media-server-account', {
			params: { path: { user_id: user.id } }
		});
		isSaving = false;
		if (error) {
			toast.error(`Failed to unlink ${mediaServer.display_name} account`);
			return;
		}
		user.media_server_accounts = user.media_server_accounts?.filter(
			(a) => a.provider !== mediaServer.name
		);
		toast.success(`Unlinked ${mediaServer.display_name} account.`);
		await refreshAll();
	}
</script>

<div class="flex items-center gap-2">
	<Popover.Root bind:open>
		<Popover.Trigger
			class={cn(buttonVariants({ variant: 'outline' }), 'w-56 justify-between font-normal')}
			disabled={isSaving}
			role="combobox"
			aria-expanded={open}
		>
			{#if linkedAccount}
				<span class="truncate">{linkedAccount.username}</span>
			{:else}
				<span class="text-muted-foreground">Not linked</span>
			{/if}
			{#if isSaving}
				<LoaderCircle class="size-4 shrink-0 animate-spin opacity-50" />
			{:else}
				<ChevronsUpDown class="size-4 shrink-0 opacity-50" />
			{/if}
		</Popover.Trigger>
		<Popover.Content class="w-72 p-0" align="start">
			<Command.Root>
				<Command.Input placeholder="Search {mediaServer.display_name} users..." />
				<Command.List>
					{#if loadError}
						<p class="px-2 py-6 text-center text-sm text-destructive">
							Could not load {mediaServer.display_name} users.
						</p>
					{:else if options === null}
						<div class="flex justify-center py-6">
							<LoaderCircle class="size-4 animate-spin text-muted-foreground" />
						</div>
					{:else}
						<Command.Empty>No users found.</Command.Empty>
						<Command.Group>
							{#each options as option (option.id)}
								{@const linkedElsewhere =
									option.linked_user_id != null && option.linked_user_id !== user.id}
								<Command.Item
									value={option.name}
									disabled={linkedElsewhere}
									onSelect={() => link(option)}
								>
									<Check
										class={cn(
											option.id === linkedAccount?.external_user_id ? 'opacity-100' : 'opacity-0'
										)}
									/>
									<span class="truncate">{option.name}</span>
									{#if linkedElsewhere}
										<span class="ml-auto truncate text-xs text-muted-foreground">
											Linked to {option.linked_user_name}
										</span>
									{/if}
								</Command.Item>
							{/each}
						</Command.Group>
					{/if}
				</Command.List>
			</Command.Root>
		</Popover.Content>
	</Popover.Root>
	{#if linkedAccount}
		<Button
			variant="ghost"
			size="icon"
			class="size-8 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
			disabled={isSaving}
			onclick={unlink}
		>
			<X class="size-4" />
			<span class="sr-only">Unlink {mediaServer.display_name} account</span>
		</Button>
	{/if}
</div>
