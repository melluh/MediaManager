<script lang="ts">
	import { getMaybeCurrentUser } from '$lib/context.svelte';
	const user = getMaybeCurrentUser();
</script>

{#if user()}
	<span class="truncate font-semibold">{user()!.display_name || user()!.email}</span>
	{#if user()!.is_superuser}
		<span class="truncate text-xs">Administrator</span>
	{:else}
		<span class="truncate text-xs">User</span>
	{/if}
{:else}
	<span class="truncate font-semibold text-muted-foreground">Signing in…</span>
{/if}
