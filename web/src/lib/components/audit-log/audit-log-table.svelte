<script lang="ts">
	import { resolve } from '$app/paths';
	import * as Table from '$lib/components/ui/table/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import UserPill from '$lib/components/user-pill.svelte';
	import type { AuditLogEntry } from '$lib/api/api';
	import { cn, formatAddedTime, formatLastUpdated } from '$lib/utils';
	import Download from '@lucide/svelte/icons/download';
	import Film from '@lucide/svelte/icons/film';
	import Tv from '@lucide/svelte/icons/tv';
	import UserRound from '@lucide/svelte/icons/user-round';
	import type { Component } from 'svelte';
	import { auditActions, describeEntry } from './audit-actions';

	let {
		entries,
		showUser = true
	}: {
		entries: AuditLogEntry[];
		/** Off when every entry is about the same user, e.g. on their own page. */
		showUser?: boolean;
	} = $props();

	/** Movies and shows link by their current slug, and not at all once deleted. */
	function subjectHref(entry: AuditLogEntry): string | null {
		switch (entry.subject_type) {
			case 'movie':
				return entry.media_slug
					? resolve('/dashboard/movies/[movieId]', { movieId: entry.media_slug })
					: null;
			case 'show':
				return entry.media_slug
					? resolve('/dashboard/tv/[showId]', { showId: entry.media_slug })
					: null;
			case 'user':
				return entry.subject_id
					? resolve('/dashboard/users/[userId]', { userId: entry.subject_id })
					: null;
			default:
				return null;
		}
	}

	/** Downloads are recorded against the torrent, but are more useful linked to their media. */
	function mediaOfTorrent(entry: AuditLogEntry): { href: string | null; label: string } | null {
		const d = entry.details as Record<string, unknown>;
		if (entry.subject_type !== 'torrent' || typeof d.media_label !== 'string') return null;
		const slug = entry.media_slug;
		const href = !slug
			? null
			: d.media_type === 'show'
				? resolve('/dashboard/tv/[showId]', { showId: slug })
				: resolve('/dashboard/movies/[movieId]', { movieId: slug });
		return { href, label: d.media_label };
	}

	const subjectIcons: Record<string, Component<{ class?: string }>> = {
		movie: Film,
		show: Tv,
		torrent: Download,
		user: UserRound
	};

	function subjectIcon(entry: AuditLogEntry) {
		const d = entry.details as Record<string, unknown>;
		// A download is shown as its media, so it gets the media's icon.
		const type =
			entry.subject_type === 'torrent' && d.media_type ? d.media_type : entry.subject_type;
		return typeof type === 'string' ? subjectIcons[type] : undefined;
	}
</script>

<Table.Root>
	<Table.Header>
		<Table.Row>
			<Table.Head>Time</Table.Head>
			{#if showUser}
				<Table.Head>User</Table.Head>
			{/if}
			<Table.Head>Action</Table.Head>
			<Table.Head>Subject</Table.Head>
			<Table.Head>Details</Table.Head>
			<Table.Head>IP address</Table.Head>
		</Table.Row>
	</Table.Header>
	<Table.Body>
		{#each entries as entry (entry.id)}
			{@const action = auditActions[entry.action]}
			{@const href = subjectHref(entry)}
			{@const media = mediaOfTorrent(entry)}
			<Table.Row>
				<Table.Cell class="whitespace-nowrap text-muted-foreground">
					<Tooltip.Root>
						<Tooltip.Trigger>
							{formatAddedTime(entry.timestamp)}
						</Tooltip.Trigger>
						<Tooltip.Content>{formatLastUpdated(entry.timestamp)}</Tooltip.Content>
					</Tooltip.Root>
				</Table.Cell>
				{#if showUser}
					<Table.Cell>
						{#if entry.actor_user_id && entry.actor_is_admin !== null}
							<UserPill
								userId={entry.actor_user_id}
								name={entry.actor_label ?? 'Unknown'}
								isAdmin={entry.actor_is_admin}
							/>
						{:else if entry.actor_label}
							<span class="text-muted-foreground" title="This user has since been deleted">
								{entry.actor_label}
							</span>
						{:else}
							<span class="text-muted-foreground">Anonymous</span>
						{/if}
					</Table.Cell>
				{/if}
				<Table.Cell>
					<span
						class={cn(
							'flex items-center gap-2 font-medium whitespace-nowrap',
							action.destructive && 'text-destructive'
						)}
					>
						<action.icon class="size-4 shrink-0" />
						{action.label}
					</span>
				</Table.Cell>
				<Table.Cell class="max-w-64">
					{@const Icon = subjectIcon(entry)}
					<div class="flex min-w-0 items-start gap-2">
						{#if Icon && entry.subject_label}
							<Icon class="mt-0.5 size-4 shrink-0 text-muted-foreground" />
						{/if}
						<div class="min-w-0">
							<!-- eslint-disable svelte/no-navigation-without-resolve -- hrefs are built from resolve() in subjectHref and mediaOfTorrent -->
							{#if media}
								{#if media.href}
									<a href={media.href} class="block truncate hover:underline">{media.label}</a>
								{:else}
									<span class="block truncate">{media.label}</span>
								{/if}
								<span class="block truncate text-xs text-muted-foreground">
									{entry.subject_label}
								</span>
							{:else if href && entry.subject_label}
								<a {href} class="block truncate hover:underline">{entry.subject_label}</a>
							{:else if entry.subject_label}
								<span class="block truncate">{entry.subject_label}</span>
							{/if}
							<!-- eslint-enable svelte/no-navigation-without-resolve -->
						</div>
					</div>
				</Table.Cell>
				<Table.Cell class="max-w-96 text-muted-foreground">
					{#each describeEntry(entry) as part, i (i)}
						<span class="block truncate" title={part}>{part}</span>
					{/each}
				</Table.Cell>
				<Table.Cell class="font-mono text-xs whitespace-nowrap text-muted-foreground">
					{#if entry.ip_address}
						<span title={entry.user_agent ?? undefined}>{entry.ip_address}</span>
					{/if}
				</Table.Cell>
			</Table.Row>
		{/each}
	</Table.Body>
</Table.Root>
