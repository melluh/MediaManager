<script lang="ts">
	import AuditLogPanel from '$lib/components/audit-log/audit-log-panel.svelte';
	import PageHeading from '$lib/components/page-heading.svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { getCurrentUser, setCrumbs } from '$lib/context.svelte';
	import { Resolved } from '$lib/hooks/resolved.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	let currentUser = getCurrentUser();
	const user = new Resolved(() => data.user, { key: () => page.params.userId });
	let name = $derived(
		user.value
			? user.value.display_name || user.value.email
			: user.value === null
				? 'Deleted user'
				: 'User'
	);
	let userHref = $derived(resolve('/dashboard/users/[userId]', { userId: page.params.userId! }));

	// Activity is admin-only. The backend enforces this; the redirect is just so a
	// non-admin who reaches the URL directly doesn't sit on an empty page.
	$effect(() => {
		if (!currentUser().is_superuser) {
			goto(resolve('/dashboard/users/[userId]', { userId: page.params.userId! }), {
				replaceState: true
			});
		}
	});

	setCrumbs(() => [
		{ label: 'Users', href: resolve('/dashboard/admin/users', {}) },
		{ label: name, href: userHref },
		{ label: 'Audit Log' }
	]);
</script>

<svelte:head>
	<title>Audit Log: {name} - MediaManager</title>
</svelte:head>

<main class="mx-auto flex w-full flex-1 flex-col gap-4 p-4 md:max-w-[80em] tablet:px-8">
	<PageHeading class="my-6">Audit Log: {name}</PageHeading>
	<AuditLogPanel log={data.log} filters={data.filters} />
</main>
