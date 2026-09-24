<script lang="ts">
	import type { Snippet } from 'svelte';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { buttonVariants } from '$lib/components/ui/button/index.js';
	import EllipsisVertical from '@lucide/svelte/icons/ellipsis-vertical';
	import type { PublicMovie, PublicShow } from '$lib/api/api';
	import LibraryCombobox from '$lib/components/library-combobox.svelte';
	import DeleteMediaDialog from '$lib/components/delete-media-dialog.svelte';
	import MediaDetailsDialog from '$lib/components/media-details-dialog.svelte';
	import { cn } from '$lib/utils';

	let {
		media,
		isShow,
		class: className,
		children
	}: {
		media: PublicMovie | PublicShow;
		isShow: boolean;
		/** Classes for the menu's content, e.g. to widen it for longer items. */
		class?: string;
		/** Media-specific items shown above the shared ones; they add their own trailing separator. */
		children?: Snippet;
	} = $props();
</script>

<DropdownMenu.Root>
	<DropdownMenu.Trigger class={buttonVariants({ variant: 'outline', size: 'icon' })}>
		<EllipsisVertical class="size-4" />
		<span class="sr-only">More actions</span>
	</DropdownMenu.Trigger>
	<DropdownMenu.Content align="end" class={cn('w-48', className)}>
		{@render children?.()}
		<MediaDetailsDialog {media} {isShow} />
		<DropdownMenu.Separator />
		<LibraryCombobox {media} mediaType={isShow ? 'tv' : 'movie'} />
		<DropdownMenu.Separator />
		<DeleteMediaDialog {media} {isShow} />
	</DropdownMenu.Content>
</DropdownMenu.Root>
