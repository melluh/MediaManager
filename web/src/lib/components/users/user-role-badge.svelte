<script lang="ts">
	import { Badge } from '$lib/components/ui/badge/index.js';
	import ShieldUser from '@lucide/svelte/icons/shield-user';
	import type { UserRead } from '$lib/api/api';

	let { user }: { user: Pick<UserRead, 'is_superuser'> } = $props();
</script>

{#if user.is_superuser}
	<Badge variant="default" class="gap-1">
		<ShieldUser class="size-3.5" />Admin
	</Badge>
{:else}
	<span class="text-sm text-muted-foreground">User</span>
{/if}
