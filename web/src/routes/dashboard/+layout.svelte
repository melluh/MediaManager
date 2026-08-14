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
	// Set by pages with a hero backdrop image behind the header: forces
	// white header text/icons and hides the mobile logo, since both only
	// make sense while that backdrop is actually showing.
	let heroHeader = $state(false);
	setContext('user', () => data.user);
	setContext('setCrumbs', (newCrumbs: Crumb[]) => {
		crumbs = newCrumbs;
	});
	setContext('setHeroHeader', (active: boolean) => {
		heroHeader = active;
	});

	if (data.user && !data.user.is_verified) {
		toast.info('Your account requires verification. Redirecting...');
		goto(resolve('/login/verify', {}));
	}
</script>

<Sidebar.Provider>
	<AppSidebar />
	<Sidebar.Inset>
		<DashboardHeader {crumbs} {heroHeader} />
		{@render children()}
	</Sidebar.Inset>
</Sidebar.Provider>
