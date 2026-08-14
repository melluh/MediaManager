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

	let { crumbs = [], heroHeader = false }: { crumbs?: Crumb[]; heroHeader?: boolean } = $props();

	let mobileSearchOpen = $state(false);
	let onSearchPage = $derived(isSearchPage(page.url.pathname));
	// The search results page always shows the expanded mobile search bar.
	let showMobileSearchExpanded = $derived(mobileSearchOpen || onSearchPage);
	let searchQuery = $derived(onSearchPage ? (page.url.searchParams.get('q') ?? '') : '');
	// Pages with a backdrop image force white text/icons here regardless of
	// the app's light/dark theme, since the header sits transparently over it.
	// text-shadow and drop-shadow are split because drop-shadow (a blur over
	// the whole element's alpha silhouette) looks muddy on small text, while
	// text-shadow doesn't apply to icon SVGs at all.
	let overlayColorClass = $derived(heroHeader ? 'text-white hover:text-white/80' : '');
	let overlayTextClass = $derived(heroHeader ? `${overlayColorClass} text-shadow-lg` : '');
	let overlayIconClass = $derived(heroHeader ? `${overlayColorClass} drop-shadow-md` : '');
</script>

<header class="relative z-20 flex h-16 shrink-0 items-center gap-2 bg-transparent">
	<div class={cn('flex items-center gap-2 px-4', showMobileSearchExpanded && 'hidden md:flex')}>
		<Sidebar.Trigger class={cn('-ml-1', overlayIconClass)} />
		<Separator class="mr-2 hidden h-4 md:block" orientation="vertical" />
		<Breadcrumb.Root class="hidden md:block">
			<Breadcrumb.List class={overlayTextClass}>
				<Breadcrumb.Item>
					<Breadcrumb.Link class={overlayTextClass} href={resolve('/dashboard', {})}>
						MediaManager
					</Breadcrumb.Link>
				</Breadcrumb.Item>
				{#each crumbs as crumb (crumb.label)}
					<Breadcrumb.Separator />
					<Breadcrumb.Item>
						{#if crumb.href}
							<Breadcrumb.Link class={overlayTextClass} href={crumb.href}>
								{crumb.label}
							</Breadcrumb.Link>
						{:else}
							<Breadcrumb.Page class={overlayTextClass}>{crumb.label}</Breadcrumb.Page>
						{/if}
					</Breadcrumb.Item>
				{/each}
			</Breadcrumb.List>
		</Breadcrumb.Root>
	</div>

	<MobileHeaderSearch
		bind:open={mobileSearchOpen}
		{onSearchPage}
		{searchQuery}
		textClass={overlayTextClass}
		iconClass={overlayIconClass}
		hideLogo={heroHeader}
	/>

	<MediaSearchBox class="mr-4 ml-auto hidden w-full max-w-md md:block" initialValue={searchQuery} />
</header>
