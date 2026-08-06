<script lang="ts" module>
	import {
		Bell,
		Clapperboard,
		Home,
		Info,
		Settings,
		TvIcon
	} from 'lucide-svelte';
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
				isActive: true,
				items: [
					{
						title: 'Add a show',
						url: resolve('/dashboard/tv/add-show', {})
					},
					{
						title: 'Torrents',
						url: resolve('/dashboard/tv/torrents', {})
					}
				]
			},
			{
				title: 'Movies',
				url: resolve('/dashboard/movies', {}),
				icon: Clapperboard,
				isActive: true,
				items: [
					{
						title: 'Add a movie',
						url: resolve('/dashboard/movies/add-movie', {})
					},
					{
						title: 'Torrents',
						url: resolve('/dashboard/movies/torrents', {})
					}
				]
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
	import NavUser from '$lib/components/nav/nav-user.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar';
	import type { ComponentProps } from 'svelte';
	import AppBrand from '$lib/components/app-brand.svelte';
	import { afterNavigate } from '$app/navigation';

	let { ref = $bindable(null), ...restProps }: ComponentProps<typeof Sidebar.Root> = $props();

	const sidebar = Sidebar.useSidebar();

	afterNavigate(() => {
		if (sidebar.isMobile) {
			sidebar.setOpenMobile(false);
		}
	});
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
		<NavSecondary class="mt-auto" items={data.navSecondary} />
	</Sidebar.Content>
	<Sidebar.Footer>
		<NavUser />
	</Sidebar.Footer>
</Sidebar.Root>
