<script lang="ts">
	import { Progress } from '$lib/components/ui/progress/index.js';
	import type { DiskUsageStats } from '$lib/api/api';
	import { formatBytes } from '$lib/utils';

	let { entries }: { entries: DiskUsageStats['entries'] } = $props();
</script>

<div class="flex flex-col gap-4">
	{#each entries as entry (entry.paths.join(','))}
		<div>
			<div class="mb-1 flex items-baseline justify-between gap-2">
				<span class="font-medium">{entry.names.join(', ')}</span>
				{#if entry.available}
					<span class="shrink-0 text-sm text-muted-foreground">
						{formatBytes(entry.used_bytes)} / {formatBytes(entry.total_bytes)} used
					</span>
				{:else}
					<span class="shrink-0 text-sm text-destructive">Path not found</span>
				{/if}
			</div>
			{#if entry.available}
				<Progress
					value={entry.total_bytes > 0 ? (entry.used_bytes / entry.total_bytes) * 100 : 0}
				/>
			{/if}
		</div>
	{/each}
</div>
