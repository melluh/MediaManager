<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Check from '@lucide/svelte/icons/check';
	import X from '@lucide/svelte/icons/x';
	import type { HTMLInputTypeAttribute } from 'svelte/elements';

	let {
		id,
		label,
		value,
		type = 'text',
		onSave,
		editable = true,
		disabledMessage
	}: {
		id: string;
		label: string;
		value: string;
		type?: HTMLInputTypeAttribute;
		onSave: (newValue: string) => Promise<boolean>;
		editable?: boolean;
		disabledMessage?: string;
	} = $props();

	let editing = $state(false);
	let draft = $state(value);
	let saving = $state(false);

	function startEdit() {
		draft = value;
		editing = true;
	}

	function cancelEdit() {
		editing = false;
	}

	async function confirmEdit() {
		if (draft === value) {
			editing = false;
			return;
		}
		saving = true;
		const success = await onSave(draft);
		saving = false;
		if (success) {
			editing = false;
		}
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			confirmEdit();
		} else if (e.key === 'Escape') {
			e.preventDefault();
			cancelEdit();
		}
	}
</script>

<div>
	<Label class="mb-1 block text-sm font-medium" for={id}>{label}</Label>
	{#if editing}
		<div class="flex items-center gap-2">
			<Input
				{id}
				{type}
				bind:value={draft}
				autofocus
				class="w-64"
				disabled={saving}
				onkeydown={onKeydown}
			/>
			<Button
				aria-label="Confirm"
				disabled={saving}
				onclick={confirmEdit}
				size="icon"
				variant="ghost"
			>
				<Check class="stroke-green-500" />
			</Button>
			<Button
				aria-label="Cancel"
				disabled={saving}
				onclick={cancelEdit}
				size="icon"
				variant="ghost"
			>
				<X class="stroke-rose-600" />
			</Button>
		</div>
	{:else if editable}
		<div class="flex items-center gap-2">
			{#if value}
				<span class="text-sm" {id}>{value}</span>
			{:else}
				<span class="text-sm text-muted-foreground italic" {id}>Not set</span>
			{/if}
			<Button aria-label="Edit {label}" onclick={startEdit} size="icon" variant="ghost">
				<Pencil class="size-4" />
			</Button>
		</div>
	{:else}
		<Tooltip.Root>
			<Tooltip.Trigger>
				{#snippet child({ props })}
					{#if value}
						<span class="text-sm" {id} {...props}>{value}</span>
					{:else}
						<span class="text-sm text-muted-foreground italic" {id} {...props}>Not set</span>
					{/if}
				{/snippet}
			</Tooltip.Trigger>
			<Tooltip.Content>{disabledMessage}</Tooltip.Content>
		</Tooltip.Root>
	{/if}
</div>
