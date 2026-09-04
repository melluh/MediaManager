<script lang="ts">
	import type { PublicMovie, PublicShow } from '$lib/api/api';
	import { toast } from 'svelte-sonner';
	import client from '$lib/api/index.ts';
	import { invalidateAll } from '$app/navigation';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import Info from '@lucide/svelte/icons/info';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';
	import { formatLastUpdated } from '$lib/utils';

	let {
		media,
		isShow
	}: {
		media: PublicMovie | PublicShow;
		isShow: boolean;
	} = $props();

	const detailsDialog = shallowDialog('mediaDetails');
	let rescanning = $state(false);

	async function rescan() {
		if (rescanning) return;
		rescanning = true;
		try {
			const { error } = isShow
				? await client.POST('/api/v1/tv/shows/{show_id}/rescan', {
						params: { path: { show_id: media.id! } }
					})
				: await client.POST('/api/v1/movies/{movie_id}/rescan', {
						params: { path: { movie_id: media.id! } }
					});
			if (error) {
				toast.error('Failed to rescan files: ' + error.detail);
			} else {
				toast.success('Files rescanned.');
				await invalidateAll();
			}
		} finally {
			rescanning = false;
		}
	}
</script>

<Dialog.Root bind:open={() => detailsDialog.open, (v) => (detailsDialog.open = v)}>
	<Dialog.Trigger>
		{#snippet child({ props })}
			<DropdownMenu.Item {...props} closeOnSelect={false}>
				<Info />
				Details
			</DropdownMenu.Item>
		{/snippet}
	</Dialog.Trigger>
	<Dialog.Content class="w-full max-w-[500px] rounded-lg p-6 shadow-lg">
		<Dialog.Header class="min-w-0">
			<Dialog.Title class="mb-1 text-xl font-semibold">Media details</Dialog.Title>
			<Dialog.Description
				>Technical details about this {isShow ? 'show' : 'movie'}.</Dialog.Description
			>
		</Dialog.Header>

		<div class="flex flex-col gap-1 rounded-lg border bg-muted/40 px-3 py-2">
			<span class="text-xs text-muted-foreground">Directory name</span>
			<span class="font-mono text-sm break-all">{media.directory_name ?? 'Not set'}</span>
		</div>

		<div class="flex flex-col gap-1 rounded-lg border bg-muted/40 px-3 py-2">
			<span class="text-xs text-muted-foreground">Added</span>
			<span class="text-sm font-medium">
				{formatLastUpdated(media.created_at) ?? 'Unknown'}
				{#if media.added_by}
					by {media.added_by.display_name || media.added_by.email}
				{/if}
			</span>
		</div>

		<Button onclick={rescan} disabled={rescanning} variant="outline" class="w-full">
			{#if rescanning}
				<LoaderCircle class="animate-spin" />
			{:else}
				<RefreshCw />
			{/if}
			Rescan files
		</Button>
	</Dialog.Content>
</Dialog.Root>
