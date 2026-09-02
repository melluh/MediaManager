<script lang="ts">
	import AppSidebar from '$lib/components/nav/app-sidebar.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import DashboardHeader, { type Crumb } from '$lib/components/nav/dashboard-header.svelte';
	import PageLoading from '$lib/components/page-loading.svelte';
	import PageLoadError from '$lib/components/page-load-error.svelte';
	import type { LayoutProps } from './$types';
	import { setContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { toast } from 'svelte-sonner';
	import type { UserRead } from '$lib/api/api';
	import { notificationCount } from '$lib/hooks/notification-count.svelte.js';
	import { serviceHealth } from '$lib/hooks/service-health.svelte.js';

	let { data, children }: LayoutProps = $props();
	let crumbs: Crumb[] = $state([]);
	// Set by pages with a hero backdrop image behind the header: forces
	// white header text/icons and hides the mobile logo, since both only
	// make sense while that backdrop is actually showing.
	let heroHeader = $state(false);

	// The user is resolved here rather than in `load` so the layout can paint a
	// loading indicator while /users/me is in flight, instead of blocking first paint.
	let user = $state<UserRead | undefined>(undefined);
	let status = $state<'loading' | 'ready' | 'error'>('loading');

	setContext('user', () => user);
	setContext('setCrumbs', (newCrumbs: Crumb[]) => {
		crumbs = newCrumbs;
	});
	setContext('setHeroHeader', (active: boolean) => {
		heroHeader = active;
	});

	$effect(() => {
		const pending = data.user;
		let cancelled = false;
		status = 'loading';

		pending.then((result) => {
			if (cancelled) return;
			if (result.state === 'unauthorized') {
				// Stay on the loading indicator, we're on our way out of the dashboard.
				goto(resolve('/login', {}));
				return;
			}
			if (result.state === 'unreachable') {
				status = 'error';
				return;
			}
			user = result.user;
			status = 'ready';
			// Only poll once we know we're authenticated, otherwise these fire 401s
			// while the session is still being established.
			notificationCount.startPolling();
			serviceHealth.startPolling();
			if (!result.user.is_verified) {
				toast.info('Your account requires verification. Redirecting...');
				goto(resolve('/login/verify', {}));
			}
		});

		return () => {
			cancelled = true;
		};
	});
</script>

{#if status === 'error'}
	<PageLoadError
		fullPage
		message="Could not reach the MediaManager backend, so your account could not be loaded. Please try again in a moment."
	/>
{:else if status === 'loading' || !user}
	<PageLoading fullPage message="Signing you in…" />
{:else}
	<Sidebar.Provider>
		<AppSidebar />
		<Sidebar.Inset>
			<DashboardHeader {crumbs} {heroHeader} />
			{@render children()}
		</Sidebar.Inset>
	</Sidebar.Provider>
{/if}
