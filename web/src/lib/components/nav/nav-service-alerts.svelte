<script lang="ts">
	import { getContext } from 'svelte';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import CircleAlert from '@lucide/svelte/icons/circle-alert';
	import HelpCircle from '@lucide/svelte/icons/help-circle';
	import ServiceHealthDialog from '$lib/components/nav/service-health-dialog.svelte';
	import type { ServiceHealth, UserRead } from '$lib/api/api';
	import { cn } from '$lib/utils';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';

	let { services }: { services: ServiceHealth[] } = $props();

	const user: () => UserRead = getContext('user');

	const alertServices = $derived(services.filter((service) => service.status !== 'healthy'));

	const statusClasses = {
		unavailable: 'border-destructive/50 bg-destructive/10 text-destructive',
		unknown: 'border-muted-foreground/30 bg-muted text-muted-foreground'
	} as const;

	const statusIcons = {
		unavailable: CircleAlert,
		unknown: HelpCircle
	} as const;
</script>

{#if alertServices.length > 0}
	<Sidebar.Group>
		<Sidebar.GroupContent class="flex flex-col gap-2">
			{#each alertServices as service (service.name)}
				{@const Icon = statusIcons[service.status as keyof typeof statusIcons]}
				{@const boxClass = cn(
					'rounded-lg border px-3 py-2 text-xs font-medium',
					statusClasses[service.status as keyof typeof statusClasses]
				)}
				{#snippet row()}
					<Icon class="size-4 shrink-0" />
					{service.display_name}
					is
					{service.status}
				{/snippet}
				{#if user().is_superuser}
					{@const dialog = shallowDialog(`serviceHealth:${service.name}`)}
					<Dialog.Root bind:open={() => dialog.open, (v) => (dialog.open = v)}>
						<Dialog.Trigger>
							{#snippet child({ props })}
								<button
									type="button"
									class={cn(boxClass, 'flex w-full cursor-pointer items-center gap-2.5 text-left')}
									{...props}
								>
									<Icon class="size-4 shrink-0" />
									<div class="flex flex-col gap-1">
										<span>{service.display_name} is {service.status}</span>
										<span class="flex items-center gap-0.5 text-xs font-normal opacity-70">
											See details
											<ArrowRight class="size-3" />
										</span>
									</div>
								</button>
							{/snippet}
						</Dialog.Trigger>
						<ServiceHealthDialog {service} />
					</Dialog.Root>
				{:else}
					<div class={cn(boxClass, 'flex items-center gap-2')}>
						{@render row()}
					</div>
				{/if}
			{/each}
		</Sidebar.GroupContent>
	</Sidebar.Group>
{/if}
