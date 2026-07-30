<script lang="ts">
	import AppSidebar from '$lib/components/nav/app-sidebar.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import DashboardHeader, { type Crumb } from '$lib/components/nav/dashboard-header.svelte';
	import type { LayoutProps } from './$types';
	import { setContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { toast } from 'svelte-sonner';

	let { data, children }: LayoutProps = $props();
	let crumbs: Crumb[] = $state([]);
	setContext('user', () => data.user);
	setContext('setCrumbs', (newCrumbs: Crumb[]) => {
		crumbs = newCrumbs;
	});

	if (data.user && !data.user.is_verified) {
		toast.info('Your account requires verification. Redirecting...');
		goto(resolve('/login/verify', {}));
	}
</script>

<Sidebar.Provider>
	<AppSidebar />
	<Sidebar.Inset>
		<DashboardHeader {crumbs} />
		{@render children()}
	</Sidebar.Inset>
</Sidebar.Provider>
