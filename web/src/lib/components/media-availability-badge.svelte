<script lang="ts">
	import { Badge, type BadgeVariant } from '$lib/components/ui/badge/index.js';
	import { Progress } from '$lib/components/ui/progress/index.js';
	import { cn } from '$lib/utils';
	import type { AvailabilityBadgeInfo, MediaAvailability } from './media-availability';

	let { availability }: { availability: MediaAvailability } = $props();

	const toneVariant: Record<AvailabilityBadgeInfo['tone'], BadgeVariant> = {
		available: 'default',
		downloading: 'outline',
		error: 'destructive',
		neutral: 'secondary'
	};

	const toneClasses: Record<AvailabilityBadgeInfo['tone'], string> = {
		available: 'border-transparent bg-green-600 text-white hover:bg-green-600',
		downloading: 'border-blue-600/50 text-blue-700 dark:text-blue-400',
		error: '',
		neutral: ''
	};
</script>

<div class="flex flex-wrap items-center gap-2">
	<Badge
		variant={toneVariant[availability.primary.tone]}
		class={toneClasses[availability.primary.tone]}
	>
		{availability.primary.label}
	</Badge>
	{#if availability.secondary}
		<div class="flex min-w-0 items-center gap-2">
			<Badge
				variant={toneVariant[availability.secondary.tone]}
				class={cn(toneClasses[availability.secondary.tone], 'shrink-0')}
			>
				{availability.secondary.label}{#if availability.secondary.progress != null}
					&nbsp;{Math.round(availability.secondary.progress)}%
				{/if}
			</Badge>
			{#if availability.secondary.progress != null}
				<Progress value={availability.secondary.progress} class="h-1.5 w-20" />
			{/if}
		</div>
	{/if}
</div>
