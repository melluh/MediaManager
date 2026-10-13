<script lang="ts">
	import { Badge } from '$lib/components/ui/badge/index.js';
	import type { UserRead } from '$lib/api/api';

	let { user }: { user: Pick<UserRead, 'is_active' | 'is_verified'> } = $props();
</script>

{#if !user.is_active}
	<Badge variant="destructive">Deactivated</Badge>
{:else if !user.is_verified}
	<Badge variant="outline">Unverified</Badge>
{:else}
	<Badge variant="secondary">Active</Badge>
{/if}
