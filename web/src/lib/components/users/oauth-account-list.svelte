<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import type { OAuthAccountRead } from '$lib/api/api';
	import { formatAddedTime } from '$lib/utils';
	import Trash2 from '@lucide/svelte/icons/trash-2';

	let {
		accounts,
		emptyMessage = 'No linked OAuth accounts.',
		onUnlink
	}: {
		accounts: OAuthAccountRead[];
		emptyMessage?: string;
		// Shows an unlink button on each account when set.
		onUnlink?: (account: OAuthAccountRead) => void;
	} = $props();
</script>

{#if accounts.length}
	<div class="flex flex-wrap gap-2">
		{#each accounts as account (account.id)}
			{@const lastUsed = formatAddedTime(account.last_used_at)}
			<div
				class="flex min-h-9 items-center gap-2 rounded-md border py-1 pl-3 text-sm font-medium {onUnlink
					? 'pr-1'
					: 'pr-3'}"
			>
				<div class="flex flex-col">
					<span>{account.oauth_name}: {account.account_email}</span>
					{#if lastUsed}
						<span class="text-xs font-normal text-muted-foreground">Last used: {lastUsed}</span>
					{/if}
				</div>
				{#if onUnlink}
					<Button
						variant="ghost"
						size="icon"
						class="size-7 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
						onclick={() => onUnlink(account)}
					>
						<Trash2 class="size-4" />
						<span class="sr-only">Unlink {account.oauth_name} account</span>
					</Button>
				{/if}
			</div>
		{/each}
	</div>
{:else}
	<p class="text-sm text-muted-foreground">{emptyMessage}</p>
{/if}
