<script lang="ts">
	import type { ImportMatchConfidence } from '$lib/api/api';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { cn } from '$lib/utils';
	import { getConfidenceMeta } from '$lib/components/import-media/confidence';
	import BadgeCheck from '@lucide/svelte/icons/badge-check';
	import Check from '@lucide/svelte/icons/check';
	import CircleAlert from '@lucide/svelte/icons/circle-alert';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';

	let { confidence }: { confidence: ImportMatchConfidence } = $props();

	const icons = {
		exact_id: BadgeCheck,
		confident: Check,
		best_guess: TriangleAlert,
		none: CircleAlert
	};

	const meta = $derived(getConfidenceMeta(confidence));
	const Icon = $derived(icons[confidence]);
</script>

<Badge variant="outline" class={cn('gap-1 whitespace-nowrap', meta.badgeClass)} title={meta.hint}>
	<Icon class="size-3.5 shrink-0" aria-hidden="true" />
	{meta.label}
</Badge>
