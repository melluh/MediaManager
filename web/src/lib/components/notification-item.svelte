<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import Check from '@lucide/svelte/icons/check';
	import MailOpen from '@lucide/svelte/icons/mail-open';
	import type { Notification } from '$lib/api/api';
	import { cn } from '$lib/utils';

	let {
		notification,
		onToggleRead
	}: {
		notification: Notification;
		/** Marks an unread notification as read, or a read one as unread. */
		onToggleRead: () => void;
	} = $props();
</script>

<div
	class={cn(
		'flex items-start justify-between gap-4 rounded-lg border p-4 shadow-sm',
		notification.read ? 'bg-card opacity-75' : 'border-primary/30 bg-primary/5'
	)}
>
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
