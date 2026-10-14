<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import MediaImage from '$lib/components/media-image.svelte';
	import Check from '@lucide/svelte/icons/check';
	import MailOpen from '@lucide/svelte/icons/mail-open';
	import type { Notification } from '$lib/api/api';
	import { resolve } from '$app/paths';
	import { cn } from '$lib/utils';

	let {
		notification,
		onToggleRead
	}: {
		notification: Notification;
		/** Marks an unread notification as read, or a read one as unread. */
		onToggleRead: () => void;
	} = $props();

	let posterLoaded = $state(false);
	let mediaHref = $derived.by(() => {
		const media = notification.media;
		if (!media) return undefined;
		const slugOrId = media.slug ?? media.id;
		return media.is_show
			? resolve('/dashboard/tv/[showId]', { showId: slugOrId })
			: resolve('/dashboard/movies/[movieId]', { movieId: slugOrId });
	});
</script>

<div
	class={cn(
		'flex items-start justify-between gap-4 rounded-lg border p-4 shadow-sm',
		notification.read ? 'bg-card opacity-75' : 'border-primary/30 bg-primary/5'
	)}
>
	{#if notification.media && mediaHref}
		<!-- eslint-disable svelte/no-navigation-without-resolve -- href is built from resolve() in mediaHref -->
		<a
			href={mediaHref}
			class="relative aspect-2/3 w-12 shrink-0 overflow-hidden rounded-md bg-muted"
			title={notification.media.name}
		>
			<!-- eslint-enable svelte/no-navigation-without-resolve -->
			<MediaImage
				media={notification.media}
				className="h-full w-full object-cover"
				bind:loaded={posterLoaded}
			/>
			{#if !posterLoaded}
				<Skeleton class="absolute inset-0 h-full w-full" />
			{/if}
		</a>
	{/if}
	<div class="flex-1">
		<p class={notification.read ? 'text-muted-foreground' : 'font-medium'}>
			{notification.message}
		</p>
		<p class="mt-1 text-sm text-muted-foreground">
			{new Date(notification.timestamp ?? 0).toLocaleDateString()}
		</p>
	</div>
	<Button
		onclick={onToggleRead}
		variant="outline"
		size="icon"
		title={notification.read ? 'Mark as unread' : 'Mark as read'}
	>
		{#if notification.read}
			<MailOpen class="size-4" />
		{:else}
			<Check class="size-4" />
		{/if}
	</Button>
</div>
