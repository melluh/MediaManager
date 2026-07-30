<script lang="ts">
	import { buttonVariants } from '$lib/components/ui/button';
	import * as Dialog from '$lib/components/ui/dialog';
	import { type Snippet } from 'svelte';

	let {
		open = $bindable(),
		triggerText,
		triggerClass = buttonVariants({ variant: 'default' }),
		triggerIcon,
		title,
		description,
		headerActions,
		children
	}: {
		open: boolean;
		triggerText: string;
		triggerClass?: string;
		triggerIcon?: Snippet;
		title: string;
		description?: string;
		headerActions?: Snippet;
		children: Snippet;
	} = $props();
</script>

<Dialog.Root bind:open>
	<Dialog.Trigger class={triggerClass}>
		{#if triggerIcon}{@render triggerIcon()}{/if}
		{triggerText}
	</Dialog.Trigger>
	<Dialog.Content class="max-h-[90vh] w-fit min-w-[80vw] overflow-y-auto">
		<Dialog.Header
			class={headerActions ? 'flex-row items-start justify-between space-y-0 pr-6' : undefined}
		>
			<div class="space-y-1.5 text-center sm:text-left">
				<Dialog.Title>{title}</Dialog.Title>
				{#if description}
					<Dialog.Description>
						{description}
					</Dialog.Description>
				{/if}
			</div>
			{#if headerActions}
				{@render headerActions()}
			{/if}
		</Dialog.Header>
		{@render children()}
	</Dialog.Content>
</Dialog.Root>
