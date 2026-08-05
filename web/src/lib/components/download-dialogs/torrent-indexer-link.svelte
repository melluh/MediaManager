<script lang="ts">
	import { ExternalLink } from 'lucide-svelte';

	let { indexer, comments }: { indexer: string | null | undefined; comments?: string | null } =
		$props();
</script>

{#if comments}
	<a
		href={comments}
		target="_blank"
		rel="noopener noreferrer external"
		class="flex shrink-0 items-center gap-1 text-sm text-muted-foreground hover:text-foreground hover:underline"
	>
		{indexer ?? 'Unknown'}
		<ExternalLink class="size-3.5" />
	</a>
{:else}
	<span class="shrink-0 text-sm text-muted-foreground">{indexer ?? 'Unknown'}</span>
{/if}
