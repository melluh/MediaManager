<script lang="ts">
	import { resolve } from '$app/paths';
	import UserRound from '@lucide/svelte/icons/user-round';

	let {
		userId,
		name
	}: {
		userId: string;
		name: string;
	} = $props();
</script>

<a
	href={resolve('/dashboard/users/[userId]', { userId })}
	class="inline-flex max-w-full items-center gap-1.5 rounded-full border bg-muted/40 px-2.5 py-1 text-sm font-medium transition-colors hover:bg-muted"
>
	<UserRound class="size-3.5 shrink-0 text-muted-foreground" />
	<span class="truncate">{name}</span>
</a>
