<script lang="ts">
	import * as Table from '$lib/components/ui/table';
	import * as Tooltip from '$lib/components/ui/tooltip';

	let {
		score,
		breakdown
	}: {
		score: number;
		breakdown?: { rule_name: string; score_modifier: number }[];
	} = $props();
</script>

{#if breakdown && breakdown.length > 0}
	<Table.Cell>
		<Tooltip.Root disableHoverableContent>
			<Tooltip.Trigger>
				{#snippet child({ props })}
					<span class="cursor-default underline decoration-dotted" {...props}>{score}</span>
				{/snippet}
			</Tooltip.Trigger>
			<Tooltip.Content>
				<ul class="space-y-0.5">
					{#each breakdown as entry, i (i)}
						<li>
							<span class={entry.score_modifier < 0 ? 'text-red-400' : 'text-green-400'}>
								{entry.score_modifier > 0 ? '+' : ''}{entry.score_modifier}
							</span>
							{entry.rule_name}
						</li>
					{/each}
				</ul>
			</Tooltip.Content>
		</Tooltip.Root>
	</Table.Cell>
{:else}
	<Table.Cell>{score}</Table.Cell>
{/if}
