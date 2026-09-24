<script lang="ts">
	import { onMount } from 'svelte';
	import { setCrumbs } from '$lib/context.svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Spinner } from '$lib/components/ui/spinner';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import NotificationItem from '$lib/components/notification-item.svelte';
	import client from '$lib/api';
	import type { Notification } from '$lib/api/api';
	import { notificationCount } from '$lib/hooks/notification-count.svelte.js';
	import { poll } from '$lib/hooks/poll.svelte';

	setCrumbs([{ label: 'Notifications' }]);

	let unreadNotifications: Notification[] = $state([]);
	let readNotifications: Notification[] = $state([]);
	let loading = $state(true);
	let loadingRead = $state(false);
	let readLoaded = $state(false);
	let showRead = $state(false);
	let markingAllAsRead = $state(false);

	async function fetchUnreadNotifications() {
		const { data } = await client.GET('/api/v1/notification/unread');
		if (data) {
			unreadNotifications = data;
			notificationCount.unread = data.length;
		}
		loading = false;
	}

	async function fetchReadNotifications() {
		const { data } = await client.GET('/api/v1/notification');
		if (data) readNotifications = data.filter((n) => n.read);
		loadingRead = false;
		readLoaded = true;
	}

	async function toggleShowRead() {
		showRead = !showRead;
		if (showRead && !readLoaded) {
			loadingRead = true;
			await fetchReadNotifications();
		}
	}

	async function markAsRead(notification: Notification) {
		const { response } = await client.PATCH('/api/v1/notification/{notification_id}/read', {
			params: { path: { notification_id: notification.id! } }
		});
		if (!response.ok) return;

		unreadNotifications = unreadNotifications.filter((n) => n.id !== notification.id);
		readNotifications = [{ ...notification, read: true }, ...readNotifications];
		notificationCount.unread = unreadNotifications.length;
	}

	async function markAsUnread(notification: Notification) {
		const { response } = await client.PATCH('/api/v1/notification/{notification_id}/unread', {
			params: { path: { notification_id: notification.id! } }
		});
		if (!response.ok) return;

		readNotifications = readNotifications.filter((n) => n.id !== notification.id);
		unreadNotifications = [{ ...notification, read: false }, ...unreadNotifications];
		notificationCount.unread = unreadNotifications.length;
	}

	async function markAllAsRead() {
		if (unreadNotifications.length === 0) return;

		try {
			markingAllAsRead = true;
			const { response } = await client.PATCH('/api/v1/notification/read');

			if (response.ok) {
				readNotifications = [
					...unreadNotifications.map((n) => ({ ...n, read: true })),
					...readNotifications
				];
				unreadNotifications = [];
				notificationCount.unread = 0;
			}
		} catch (error) {
			console.error('Failed to mark all notifications as read:', error);
		} finally {
			markingAllAsRead = false;
		}
	}

	// This page keeps the unread count up to date itself while it's open.
	onMount(() => {
		notificationCount.pausePolling();
		return () => notificationCount.resumePolling();
	});

	poll(async () => {
		await fetchUnreadNotifications();
		if (showRead) await fetchReadNotifications();
	}, 30000);
</script>

<svelte:head>
	<title>Notifications - MediaManager</title>
</svelte:head>

<main class="container mx-auto px-4 py-8">
	<div class="mb-6 flex items-center justify-between">
		<h1 class="text-3xl font-bold">Notifications</h1>
		{#if unreadNotifications.length > 0}
			<Button onclick={markAllAsRead} disabled={markingAllAsRead}>
				{#if markingAllAsRead}
					<Spinner class="size-4" />
				{/if}
				Mark All as Read
			</Button>
		{/if}
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-12">
			<Spinner class="size-8" />
		</div>
	{:else}
		<section class="mb-8">
			<h2 class="mb-4 text-xl font-semibold">
				Unread Notifications
				{#if unreadNotifications.length > 0}
					({unreadNotifications.length})
				{/if}
			</h2>

			{#if unreadNotifications.length === 0}
				<div
					class="rounded-lg border border-green-200 bg-green-50 p-6 text-center dark:border-green-800 dark:bg-green-900/20"
				>
					<p class="font-medium text-green-800 dark:text-green-200">All caught up!</p>
					<p class="text-sm text-green-600 dark:text-green-400">No unread notifications</p>
				</div>
			{:else}
				<div class="space-y-3">
					{#each unreadNotifications as notification (notification.id)}
						<NotificationItem {notification} onToggleRead={() => markAsRead(notification)} />
					{/each}
				</div>
			{/if}
		</section>

		<button
			onclick={toggleShowRead}
			class="mb-4 flex items-center gap-2 text-muted-foreground transition-colors hover:text-foreground"
		>
			<ChevronRight class="size-4 transition-transform {showRead ? 'rotate-90' : ''}" />
			<span>Read Notifications{readLoaded ? ` (${readNotifications.length})` : ''}</span>
		</button>

		{#if showRead}
			{#if loadingRead}
				<div class="flex items-center justify-center py-12">
					<Spinner class="size-8" />
				</div>
			{:else if readNotifications.length === 0}
				<div class="rounded-lg border bg-muted p-6 text-center">
					<p class="text-muted-foreground">No read notifications</p>
				</div>
			{:else}
				<div class="space-y-3">
					{#each readNotifications as notification (notification.id)}
						<NotificationItem {notification} onToggleRead={() => markAsUnread(notification)} />
					{/each}
				</div>
			{/if}
		{/if}
	{/if}
</main>
