<script lang="ts">
	import { resolve } from '$app/paths';
	import UserRound from '@lucide/svelte/icons/user-round';
	import ShieldUser from '@lucide/svelte/icons/shield-user';

	let {
		userId,
		name,
		isAdmin = false
	}: {
		userId: string;
		name: string;
		isAdmin?: boolean;
	} = $props();
</script>

<a
	href={resolve('/dashboard/users/[userId]', { userId })}
	class="inline-flex max-w-full items-center gap-1.5 rounded-full border bg-muted/40 px-2.5 py-1 text-sm font-medium transition-colors hover:bg-muted"
>
	{#if isAdmin}
		<ShieldUser class="size-3.5 shrink-0 text-muted-foreground" aria-label="Admin" />
	{:else}
		<UserRound class="size-3.5 shrink-0 text-muted-foreground" />
	{/if}
	<span class="truncate">{name}</span>
</a>
