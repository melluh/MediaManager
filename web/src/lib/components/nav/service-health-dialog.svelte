<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import CircleAlert from '@lucide/svelte/icons/circle-alert';
	import HelpCircle from '@lucide/svelte/icons/help-circle';
	import type { ServiceHealth } from '$lib/api/api';
	import { cn, formatAddedTime } from '$lib/utils';

	let { service }: { service: ServiceHealth } = $props();

	const statusClasses = {
		unavailable: 'border-destructive/50 bg-destructive/10 text-destructive',
		unknown: 'border-muted-foreground/30 bg-muted text-muted-foreground'
	} as const;

	const statusIcons = {
		unavailable: CircleAlert,
		unknown: HelpCircle
	} as const;

	const Icon = $derived(statusIcons[service.status as keyof typeof statusIcons]);
	const lastCheckedLabel = $derived(formatAddedTime(service.last_checked));
	const lastHealthyLabel = $derived(formatAddedTime(service.last_healthy));
</script>

<Dialog.Content class="w-full max-w-[500px] rounded-lg p-6 shadow-lg">
	<Dialog.Header>
		<Dialog.Title class="text-xl font-semibold">{service.display_name}</Dialog.Title>
	</Dialog.Header>

	<div
		class={cn(
			'flex flex-col gap-1 rounded-lg border px-3 py-2 text-sm font-medium',
			statusClasses[service.status as keyof typeof statusClasses]
		)}
	>
		<div class="flex items-center gap-2">
			<Icon class="size-4 shrink-0" />
			Status:
			{service.status}
		</div>
	</div>

	{#if service.message}
		<p class="min-w-0 font-mono text-xs font-normal break-words whitespace-pre-wrap">
			{service.message}
		</p>
	{/if}

	<div class="flex flex-col gap-1 text-sm text-muted-foreground">
		<p>Last checked: {lastCheckedLabel ?? 'n/a'}</p>
		<p>Last healthy: {lastHealthyLabel ?? 'n/a'}</p>
	</div>
</Dialog.Content>
