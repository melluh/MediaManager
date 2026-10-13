<script lang="ts">
	import type { DiskUsageCategory, DiskUsageStats } from '$lib/api/api';
	import { formatBytes } from '$lib/utils';

	let { entries }: { entries: DiskUsageStats['entries'] } = $props();

	// Theme chart tokens, so each category keeps its color in light and dark.
	const categoryColors: Record<DiskUsageCategory['key'], string> = {
		movies: 'var(--chart-1)',
		tv: 'var(--chart-2)',
		images: 'var(--chart-4)',
		other: 'color-mix(in oklab, var(--muted-foreground) 45%, transparent)'
	};

	function percentOf(bytes: number, total: number): number {
		return total > 0 ? (bytes / total) * 100 : 0;
	}
</script>

<div class="flex flex-col gap-6">
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
				<div class="flex h-3 w-full overflow-hidden rounded-full bg-muted">
					{#each entry.categories as category (category.key)}
						<div
							class="h-full"
							style:width="{percentOf(category.bytes, entry.total_bytes)}%"
							style:background-color={categoryColors[category.key]}
							title="{category.label}: {formatBytes(category.bytes)}"
						></div>
					{/each}
				</div>
				<ul class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
					{#each entry.categories as category (category.key)}
						<li class="flex items-center gap-1.5">
							<span
								class="size-2.5 shrink-0 rounded-full"
								style:background-color={categoryColors[category.key]}
							></span>
							<span>{category.label}</span>
							<span class="text-foreground">{formatBytes(category.bytes)}</span>
						</li>
					{/each}
					<li class="flex items-center gap-1.5">
						<span class="size-2.5 shrink-0 rounded-full border bg-muted"></span>
						<span>Free</span>
						<span class="text-foreground">{formatBytes(entry.free_bytes)}</span>
					</li>
				</ul>
			{/if}
		</div>
	{/each}
</div>
