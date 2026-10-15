<script lang="ts">
	import { resolve } from '$app/paths';
	import UserAvatar from '$lib/components/user-avatar.svelte';
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
	class="inline-flex max-w-full items-center gap-1.5 rounded-full border bg-muted/40 py-1 pr-2.5 pl-1 text-sm font-medium transition-colors hover:bg-muted"
>
	<UserAvatar {userId} class="size-5" />
	<span class="truncate">{name}</span>
	{#if isAdmin}
		<ShieldUser class="size-3.5 shrink-0 text-muted-foreground" aria-label="Admin" />
	{/if}
</a>
