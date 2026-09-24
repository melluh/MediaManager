<script lang="ts" generics="T extends string | number">
	import type { Component } from 'svelte';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { buttonVariants } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';

	type Option = { value: T; label: string };

	let {
		icon: Icon,
		label,
		options,
		pinnedOptions = [],
		selected = $bindable()
	}: {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		icon: Component<any>;
		label: string;
		options: Option[];
		/** Listed above `options`, separated from them (e.g. a "None" choice). */
		pinnedOptions?: Option[];
		selected: T[];
	} = $props();

	function toggle(value: T) {
		selected = selected.includes(value)
			? selected.filter((v) => v !== value)
			: [...selected, value];
	}
</script>

{#snippet optionItem(option: Option)}
	<DropdownMenu.CheckboxItem
		checked={selected.includes(option.value)}
		closeOnSelect={false}
		onCheckedChange={() => toggle(option.value)}
	>
		{option.label}
	</DropdownMenu.CheckboxItem>
{/snippet}

<DropdownMenu.Root>
	<DropdownMenu.Trigger class={buttonVariants({ variant: 'outline' })}>
		<Icon class="size-4 text-muted-foreground" />
		{label}
		{#if selected.length > 0}
			<Badge variant="secondary" class="ml-1">{selected.length}</Badge>
		{/if}
	</DropdownMenu.Trigger>
	<DropdownMenu.Content align="start" class="max-h-80 overflow-y-auto">
		{#each pinnedOptions as option (option.value)}
			{@render optionItem(option)}
		{/each}
		{#if pinnedOptions.length > 0 && options.length > 0}
			<DropdownMenu.Separator />
		{/if}
		{#each options as option (option.value)}
			{@render optionItem(option)}
		{/each}
	</DropdownMenu.Content>
</DropdownMenu.Root>
