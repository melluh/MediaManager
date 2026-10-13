<script lang="ts">
	import { Progress } from '$lib/components/ui/progress/index.js';
	import type { AvailabilityBadgeInfo, MediaAvailability } from './media-availability';

	let { availability }: { availability: MediaAvailability } = $props();

	const toneClasses: Record<AvailabilityBadgeInfo['tone'], string> = {
		available: 'text-muted-foreground',
		downloading: 'text-blue-700 dark:text-blue-400',
		error: 'text-destructive',
		neutral: 'text-muted-foreground'
	};
</script>

<!-- No wrapper: each line is laid out (and aligned) by the parent. -->
<p class="text-sm {toneClasses[availability.primary.tone]}">{availability.primary.label}</p>
{#if availability.secondary}
	<div class="flex items-center gap-2 text-sm {toneClasses[availability.secondary.tone]}">
		<span>
			{availability.secondary.label}{#if availability.secondary.progress != null}
				&nbsp;{Math.round(availability.secondary.progress)}%
			{/if}
		</span>
		{#if availability.secondary.progress != null}
			<Progress value={availability.secondary.progress} class="h-1.5 w-20" />
		{/if}
	</div>
{/if}
