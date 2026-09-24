<script lang="ts">
	import AppSidebar from '$lib/components/nav/app-sidebar.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import DashboardHeader from '$lib/components/nav/dashboard-header.svelte';
	import PageLoading from '$lib/components/page-loading.svelte';
	import PageLoadError from '$lib/components/page-load-error.svelte';
	import type { LayoutProps } from './$types';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { toast } from 'svelte-sonner';
	import { notificationCount } from '$lib/hooks/notification-count.svelte.js';
	import { serviceHealth } from '$lib/hooks/service-health.svelte.js';
	import { Resolved } from '$lib/hooks/resolved.svelte';
	import {
		setCrumbSetter,
		setHeroHeaderSetter,
		setUserContext,
		type Crumb,
		type LoadStatus
	} from '$lib/context.svelte';

	let { data, children }: LayoutProps = $props();
	let crumbs: Crumb[] = $state([]);
	// Set by pages with a hero backdrop image behind the header: forces
	// white header text/icons and hides the mobile logo, since both only
	// make sense while that backdrop is actually showing.
	let heroHeader = $state(false);

	// The user is resolved here rather than in `load` so the layout can paint a
	// loading indicator while /users/me is in flight, instead of blocking first paint.
	// A background refresh (e.g. refreshAll()/invalidateAll() from elsewhere in the
	// app) keeps the previous user while the new one loads; regressing to 'loading'
	// would tear down and remount the whole dashboard on every such refresh, wiping
	// any page-local state (like an open dialog) beneath it.
	const userResult = new Resolved(() => data.user);
	let user = $derived(userResult.value?.state === 'ok' ? userResult.value.user : undefined);
	// 'unauthorized' stays on the loading indicator: we're on our way out of the dashboard.
	let status: LoadStatus = $derived(
		userResult.value?.state === 'ok'
			? 'ready'
			: userResult.value?.state === 'unreachable'
				? 'error'
				: 'loading'
	);

	setUserContext(() => user);
	setCrumbSetter((newCrumbs) => {
		crumbs = newCrumbs;
	});
	setHeroHeaderSetter((active) => {
		heroHeader = active;
	});

	$effect(() => {
		const result = userResult.value;
		if (result?.state === 'unauthorized') {
			goto(resolve('/login', {}));
		} else if (result?.state === 'ok') {
			// Only poll once we know we're authenticated, otherwise these fire 401s
			// while the session is still being established.
			notificationCount.startPolling();
			serviceHealth.startPolling();
			if (!result.user.is_verified) {
				toast.info('Your account requires verification. Redirecting...');
				goto(resolve('/login/verify', {}));
			}
		}
	});
</script>

{#if status === 'error'}
	<PageLoadError
		fullPage
		message="Could not reach the MediaManager backend, so your account could not be loaded. Please try again in a moment."
	/>
{:else}
	<Sidebar.Provider>
		<AppSidebar />
		<Sidebar.Inset>
			<DashboardHeader {crumbs} {heroHeader} />
			{#if status === 'ready'}
				{@render children()}
			{:else}
				<PageLoading message="Signing you in…" />
			{/if}
		</Sidebar.Inset>
	</Sidebar.Provider>
{/if}
