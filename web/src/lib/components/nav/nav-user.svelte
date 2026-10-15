<script lang="ts">
	import EllipsisVertical from '@lucide/svelte/icons/ellipsis-vertical';
	import LogOut from '@lucide/svelte/icons/log-out';
	import Wrench from '@lucide/svelte/icons/wrench';
	import * as Avatar from '$lib/components/ui/avatar';
	import UserAvatar from '$lib/components/user-avatar.svelte';
	import { getMaybeCurrentUser } from '$lib/context.svelte';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Sidebar from '$lib/components/ui/sidebar';
	import { useSidebar } from '$lib/components/ui/sidebar';
	import UserDetails from './user-details.svelte';
	import UserRound from '@lucide/svelte/icons/user-round';
	import { handleLogout } from '$lib/utils.ts';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	const sidebar = useSidebar();
	const user = getMaybeCurrentUser();
</script>

<Sidebar.Menu>
	<Sidebar.MenuItem>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Sidebar.MenuButton
						{...props}
						size="lg"
						class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
					>
						{#if user()}
							<UserAvatar userId={user()!.id} class="size-8! rounded-lg" />
						{:else}
							<Avatar.Root class="size-8 rounded-lg">
								<Avatar.Fallback class="rounded-lg">
									<UserRound />
								</Avatar.Fallback>
							</Avatar.Root>
						{/if}
						<div class="grid flex-1 text-left text-sm leading-tight">
							<UserDetails />
						</div>
						<EllipsisVertical class="ml-auto size-4" />
					</Sidebar.MenuButton>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content
				align="end"
				class="w-(--bits-dropdown-menu-anchor-width) min-w-56 rounded-lg"
				side={sidebar.isMobile ? 'bottom' : 'right'}
				sideOffset={4}
			>
				<DropdownMenu.Item onclick={() => goto(resolve('/dashboard/settings#me', {}))}>
					<Wrench />
					My Account
				</DropdownMenu.Item>
				<DropdownMenu.Item onclick={() => handleLogout()}>
					<LogOut />
					Log out
				</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</Sidebar.MenuItem>
</Sidebar.Menu>
