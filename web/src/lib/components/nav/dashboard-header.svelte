<script module lang="ts">
	export interface Crumb {
		label: string;
		href?: string;
	}
</script>

<script lang="ts">
	import { Separator } from '$lib/components/ui/separator/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import * as Breadcrumb from '$lib/components/ui/breadcrumb/index.js';
	import MediaSearchBox from '$lib/components/media-search-box.svelte';
	import MobileHeaderSearch from './mobile-header-search.svelte';
	import { resolve } from '$app/paths';
	import { cn, isSearchPage } from '$lib/utils.js';
	import { page } from '$app/state';

	let { crumbs = [] }: { crumbs?: Crumb[] } = $props();

	let mobileSearchOpen = $state(false);
	let onSearchPage = $derived(isSearchPage(page.url.pathname));
	// The search results page always shows the expanded mobile search bar.
	let showMobileSearchExpanded = $derived(mobileSearchOpen || onSearchPage);
	let searchQuery = $derived(onSearchPage ? (page.url.searchParams.get('q') ?? '') : '');
</script>

<header class="flex h-16 shrink-0 items-center gap-2">
	<div class={cn('flex items-center gap-2 px-4', showMobileSearchExpanded && 'hidden md:flex')}>
		<Sidebar.Trigger class="-ml-1" />
		<Separator class="mr-2 hidden h-4 md:block" orientation="vertical" />
		<Breadcrumb.Root class="hidden md:block">
			<Breadcrumb.List>
				<Breadcrumb.Item>
					<Breadcrumb.Link href={resolve('/dashboard', {})}>MediaManager</Breadcrumb.Link>
				</Breadcrumb.Item>
				{#each crumbs as crumb (crumb.label)}
					<Breadcrumb.Separator />
					<Breadcrumb.Item>
						{#if crumb.href}
							<Breadcrumb.Link href={crumb.href}>{crumb.label}</Breadcrumb.Link>
						{:else}
							<Breadcrumb.Page>{crumb.label}</Breadcrumb.Page>
						{/if}
					</Breadcrumb.Item>
				{/each}
			</Breadcrumb.List>
		</Breadcrumb.Root>
	</div>

	<MobileHeaderSearch bind:open={mobileSearchOpen} {onSearchPage} {searchQuery} />

	<MediaSearchBox class="mr-4 ml-auto hidden w-full max-w-md md:block" initialValue={searchQuery} />
</header>
