<script lang="ts">
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import RatingIcon from '$lib/components/rating-icon.svelte';
	import { RATING_OPTIONS } from '$lib/rating';
	import { cn } from '$lib/utils';

	let {
		value = null,
		pending = false,
		onSelect,
		class: className
	}: {
		/** The selected score, highlighted on the scale. */
		value?: number | null;
		/**
		 * Whether `value` is still being saved. It's shown in a lighter, pulsing
		 * color meanwhile, and further clicks are ignored. The buttons aren't
		 * disabled, as fading them all out for a quick request reads as a flicker.
		 */
		pending?: boolean;
		onSelect: (score: number) => void;
		/**
		 * Compact by default. Make it a block-level flex container that's given
		 * more width (e.g. `flex w-full`) to spread the options across it.
		 */
		class?: string;
	} = $props();
</script>

<!-- One control rather than separate buttons, so it reads as a scale from
     loved to hated. Labels live in tooltips to keep it compact. -->
<div
	class={cn(
		'inline-flex shrink-0 items-center gap-0.5 rounded-md border bg-background p-0.5 md:h-9',
		className
	)}
	role="group"
	aria-label="Your rating"
	aria-busy={pending}
>
	{#each RATING_OPTIONS as option (option.score)}
		{@const active = value === option.score}
		<Tooltip.Root>
			<Tooltip.Trigger>
				{#snippet child({ props })}
					<button
						{...props}
						type="button"
						class={cn(
							// Icon-sized, but growing evenly into any extra width. Square on
							// mobile, where the scale is usually stretched to full width,
							// for bigger touch targets with room for a label.
							'inline-flex aspect-square min-w-8 grow basis-8 cursor-pointer flex-col items-center justify-center gap-2 rounded-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:ring-1 focus-visible:ring-ring focus-visible:outline-none md:aspect-auto md:h-8 md:flex-row [&_svg]:size-4',
							active &&
								(option.score > 0
									? pending
										? 'bg-brand/5 text-brand/60 hover:bg-brand/5 hover:text-brand/60'
										: 'bg-brand/10 text-brand hover:bg-brand/15 hover:text-brand'
									: pending
										? 'bg-destructive/5 text-destructive/60 hover:bg-destructive/5 hover:text-destructive/60'
										: 'bg-destructive/10 text-destructive hover:bg-destructive/15 hover:text-destructive'),
							active && pending && 'animate-pulse'
						)}
						aria-label={option.label}
						aria-pressed={active}
						onclick={() => {
							if (!pending) onSelect(option.score);
						}}
					>
						<RatingIcon score={option.score} filled={active} />
						<!-- Mobile has no hover tooltips, so the label is spelled out. -->
						<span class="text-xs leading-none whitespace-nowrap md:hidden" aria-hidden="true">
							{option.label}
						</span>
					</button>
				{/snippet}
			</Tooltip.Trigger>
			<Tooltip.Content>
				{active ? `${option.label} (click to remove)` : option.label}
			</Tooltip.Content>
		</Tooltip.Root>
	{/each}
</div>
