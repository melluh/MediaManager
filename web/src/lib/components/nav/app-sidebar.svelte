<script lang="ts" module>
	import Bell from '@lucide/svelte/icons/bell';
	import Clapperboard from '@lucide/svelte/icons/clapperboard';
	import Home from '@lucide/svelte/icons/home';
	import Info from '@lucide/svelte/icons/info';
	import Settings from '@lucide/svelte/icons/settings';
	import TvIcon from '@lucide/svelte/icons/tv';
	import { resolve } from '$app/paths';

	const data = {
		navMain: [
			{
				title: 'Dashboard',
				url: resolve('/dashboard', {}),
				icon: Home,
				isActive: true
			},
			{
				title: 'TV',
				url: resolve('/dashboard/tv', {}),
				icon: TvIcon,
				isActive: true
			},
			{
				title: 'Movies',
				url: resolve('/dashboard/movies', {}),
				icon: Clapperboard,
				isActive: true
			}
		],
		navSecondary: [
			{
				title: 'Notifications',
				url: resolve('/dashboard/notifications', {}),
				icon: Bell
			},
			{
				title: 'Settings',
				url: resolve('/dashboard/settings', {}),
				icon: Settings
			},
			{
				title: 'About',
				url: resolve('/dashboard/about', {}),
				icon: Info
			}
		]
	};
</script>

<script lang="ts">
	import NavMain from '$lib/components/nav/nav-main.svelte';
	import NavSecondary from '$lib/components/nav/nav-secondary.svelte';
	import NavServiceAlerts from '$lib/components/nav/nav-service-alerts.svelte';
	import NavUser from '$lib/components/nav/nav-user.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar';
	import type { ComponentProps } from 'svelte';
	import AppBrand from '$lib/components/app-brand.svelte';
	import { afterNavigate } from '$app/navigation';
	import { notificationCount } from '$lib/hooks/notification-count.svelte.js';
	import { serviceHealth } from '$lib/hooks/service-health.svelte.js';

	let { ref = $bindable(null), ...restProps }: ComponentProps<typeof Sidebar.Root> = $props();

	const sidebar = Sidebar.useSidebar();

	afterNavigate(() => {
		if (sidebar.isMobile) {
			sidebar.setOpenMobile(false);
		}
	});

	const navSecondaryItems = $derived(
		data.navSecondary.map((item) =>
			item.title === 'Notifications' ? { ...item, badge: notificationCount.unread } : item
		)
	);
</script>

<Sidebar.Root {...restProps} bind:ref variant="inset">
	{#if !sidebar.isMobile}
		<Sidebar.Header>
			<Sidebar.Menu>
				<Sidebar.MenuItem>
					<Sidebar.MenuButton size="lg">
						{#snippet child({ props })}
							<a href={resolve('/dashboard', {})} {...props}>
								<AppBrand size="md" showVersion />
							</a>
						{/snippet}
					</Sidebar.MenuButton>
				</Sidebar.MenuItem>
			</Sidebar.Menu>
		</Sidebar.Header>
	{/if}
	<Sidebar.Content>
		<NavMain items={data.navMain} />
		<!--  <NavProjects projects={data.projects}/> -->
		<div class="mt-auto flex flex-col gap-2">
			<NavServiceAlerts services={serviceHealth.services} />
			<NavSecondary items={navSecondaryItems} />
		</div>
	</Sidebar.Content>
	<Sidebar.Footer>
		<NavUser />
	</Sidebar.Footer>
</Sidebar.Root>
