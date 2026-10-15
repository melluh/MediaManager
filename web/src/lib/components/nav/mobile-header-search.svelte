<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import MediaSearchBox from '$lib/components/media-search-box.svelte';
	import AppBrand from '$lib/components/app-brand.svelte';
	import { resolve } from '$app/paths';
	import { afterNavigate, goto } from '$app/navigation';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Search from '@lucide/svelte/icons/search';
	import { cn } from '$lib/utils.js';

	let {
		open = $bindable(false),
		onSearchPage,
		searchQuery,
		textClass = '',
		iconClass = '',
		hideLogo = false
	}: {
		open?: boolean;
		onSearchPage: boolean;
		searchQuery: string;
		textClass?: string;
		iconClass?: string;
		hideLogo?: boolean;
	} = $props();

	// The search results page always shows the expanded mobile search bar,
	// even if the user didn't get here by tapping the search icon.
	let showExpanded = $derived(open || onSearchPage);

	// Tracks whether there is an in-app page behind us to go back to, as opposed
	// to having landed here via a hard navigation (direct link/refresh), where
	// history.back() would leave the app entirely.
	let hasInAppHistory = $state(false);
	afterNavigate(({ from }) => {
		if (from) hasInAppHistory = true;
	});

	function close() {
		open = false;
		if (onSearchPage) {
			if (hasInAppHistory) {
				history.back();
			} else {
				goto(resolve('/dashboard', {}));
			}
		}
	}
</script>

{#if showExpanded}
	<div class="flex w-full items-center gap-2 px-4 lg:hidden tablet:px-8">
		<Button variant="ghost" size="icon" class="h-7 w-7 shrink-0" onclick={close}>
			<ArrowLeft />
			<span class="sr-only">Close search</span>
		</Button>
		<MediaSearchBox
			class="w-full"
			autofocus={open}
			initialValue={searchQuery}
			onResultSelect={() => (open = false)}
		/>
	</div>
{/if}
{#if !hideLogo}
	<!-- Landscape tablets get the desktop header, but keep the logo centered in
	     it like on mobile; there it's absolutely positioned so the breadcrumbs
	     and search box on either side don't push it off-center. -->
	<a
		class={cn(
			'flex flex-1 items-center justify-center gap-2 lg:hidden',
			showExpanded && 'hidden',
			'lg:pointer-coarse:absolute lg:pointer-coarse:left-1/2 lg:pointer-coarse:flex lg:pointer-coarse:-translate-x-1/2',
			textClass
		)}
		href={resolve('/dashboard', {})}
	>
		<AppBrand size="sm" />
	</a>
{/if}

<Button
	variant="ghost"
	size="icon"
	class={cn('mr-4 ml-auto h-7 w-7 lg:hidden tablet:mr-8', showExpanded && 'hidden', iconClass)}
	onclick={() => (open = true)}
>
	<Search />
	<span class="sr-only">Open search</span>
</Button>
