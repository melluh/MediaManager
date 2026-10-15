<script lang="ts">
	import AuditLogPanel from '$lib/components/audit-log/audit-log-panel.svelte';
	import PageHeading from '$lib/components/page-heading.svelte';
	import * as Select from '$lib/components/ui/select/index.js';
	import { resolve } from '$app/paths';
	import { setCrumbs } from '$lib/context.svelte';
	import { Resolved } from '$lib/hooks/resolved.svelte';
	import ShieldUser from '@lucide/svelte/icons/shield-user';
	import UserRound from '@lucide/svelte/icons/user-round';
	import Users from '@lucide/svelte/icons/users';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	setCrumbs([
		{ label: 'Administration', href: resolve('/dashboard/admin', {}) },
		{ label: 'Activity' }
	]);

	const users = new Resolved(() => data.users);
	let sortedUsers = $derived(
		[...(users.value ?? [])].sort((a, b) =>
			(a.display_name || a.email).localeCompare(b.display_name || b.email)
		)
	);
	let selectedUser = $derived(users.value?.find((u) => u.id === data.filters.userId));

	const ALL = 'all';
</script>

<svelte:head>
	<title>Activity - MediaManager</title>
	<meta content="What users have done, and when" name="description" />
</svelte:head>

{#snippet userOption(label: string, Icon: typeof UserRound)}
	<div class="flex min-w-0 items-center gap-2">
		<Icon class="size-4 shrink-0 text-muted-foreground" />
		<span class="truncate">{label}</span>
	</div>
{/snippet}

<main class="mx-auto flex w-full flex-1 flex-col gap-4 p-4 md:max-w-[80em]">
	<PageHeading class="my-6">Activity</PageHeading>

	<AuditLogPanel log={data.log} filters={data.filters}>
		{#snippet extraFilters(setParams)}
			<Select.Root
				type="single"
				value={data.filters.userId ?? ALL}
				onValueChange={(value) => setParams({ user: value === ALL ? null : value, page: null })}
			>
				<Select.Trigger class="w-56">
					{@render userOption(
						selectedUser
							? selectedUser.display_name || selectedUser.email
							: data.filters.userId
								? 'Deleted user'
								: 'All users',
						selectedUser ? (selectedUser.is_superuser ? ShieldUser : UserRound) : Users
					)}
				</Select.Trigger>
				<Select.Content>
					<Select.Item value={ALL} label="All users">
						{@render userOption('All users', Users)}
					</Select.Item>
					{#each sortedUsers as user (user.id)}
						{@const label = user.display_name || user.email}
						<Select.Item value={user.id} {label}>
							{@render userOption(label, user.is_superuser ? ShieldUser : UserRound)}
						</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		{/snippet}
	</AuditLogPanel>
</main>
