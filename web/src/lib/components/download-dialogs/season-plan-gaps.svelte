<script lang="ts">
	import { gapLabel, type PlanGap } from '$lib/components/download-dialogs/season-plan';

	let { gaps }: { gaps: PlanGap[] } = $props();
</script>

<div class="rounded-md border border-amber-500/50 bg-amber-500/10 p-3 text-sm">
	<p class="font-medium">No suitable torrent found for:</p>
	<ul class="list-inside list-disc">
		{#each gaps as gap (gap.season_number)}
			<li>{gapLabel(gap)} - {gap.reason}</li>
		{/each}
	</ul>
</div>
