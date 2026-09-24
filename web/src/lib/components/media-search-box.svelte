<script lang="ts">
	import { Input } from '$lib/components/ui/input/index.js';
	import MediaImage from '$lib/components/media-image.svelte';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Search from '@lucide/svelte/icons/search';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import Plus from '@lucide/svelte/icons/plus';
	import { resolve } from '$app/paths';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import client from '$lib/api';
	import type { CombinedSearchResult } from '$lib/api/api.d.ts';
	import { cn, isSearchPage } from '$lib/utils.js';
	import { getMediaTypeHref, getMediaTypeLabel } from '$lib/media-types.ts';
	import { SvelteURLSearchParams } from 'svelte/reactivity';

	let {
		class: className = '',
		autofocus = false,
		initialValue = '',
		onResultSelect
	}: {
		class?: string;
		autofocus?: boolean;
		initialValue?: string;
		onResultSelect?: () => void;
	} = $props();

	// Writable $derived: overridden by typing, but resyncs whenever initialValue
	// changes (e.g. the desktop search box persists across client-side
	// navigations, including back/forward).
	let searchTerm = $derived(initialValue);
	// One flat, already-ranked list from the backend (in-library items mixed
	// with not-yet-added suggestions) - library items normally rank first,
	// but an exceptionally strong suggestion can surface above a weak
	// library match. See SearchService.combined_search.
	let items: CombinedSearchResult[] = $state([]);
	let hasSearched = $state(false);
	let isOpen = $state(false);
	let isLoading = $state(false);
	let hasError = $state(false);
	let highlightedIndex = $state(-1);
	let posterLoaded: Record<string, boolean> = $state({});
	let containerRef: HTMLDivElement | undefined = $state();
	let inputRef: HTMLInputElement | null = $state(null);
	let debounceTimer: ReturnType<typeof setTimeout> | undefined;
	let searchAbortController: AbortController | undefined;

	function itemKey(item: CombinedSearchResult): string {
		return item.in_library
			? `lib-${item.media_type}-${item.id}`
			: `sug-${item.media_type}-${item.external_id}`;
	}

	function hrefForItem(item: CombinedSearchResult): string | undefined {
		if (!item.in_library || !item.slug) return undefined;
		return getMediaTypeHref(item.media_type, item.slug);
	}

	function rowClass(index: number): string {
		return cn(
			'flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm',
			index === highlightedIndex
				? 'bg-accent text-accent-foreground'
				: 'hover:bg-accent hover:text-accent-foreground'
		);
	}

	function cancelPendingSearch() {
		clearTimeout(debounceTimer);
		searchAbortController?.abort();
		isLoading = false;
	}

	function clearSearch() {
		cancelPendingSearch();
		searchTerm = '';
		items = [];
		hasSearched = false;
		isOpen = false;
		highlightedIndex = -1;
		hasError = false;
	}

	$effect(() => {
		if (!isSearchPage(page.url.pathname)) {
			clearSearch();
		}
	});

	$effect(() => {
		if (autofocus) {
			inputRef?.focus();
			inputRef?.select();
		}
	});

	async function runSearch(query: string) {
		searchAbortController?.abort();
		const controller = new AbortController();
		searchAbortController = controller;
		isLoading = true;
		hasError = false;

		try {
			const { data, error } = await client.GET('/api/v1/search/combined', {
				params: { query: { q: query } },
				signal: controller.signal
			});
			if (controller.signal.aborted) return;
			if (error) {
				hasError = true;
				items = [];
			} else {
				items = data ?? [];
				for (const item of items) {
					if (item.in_library && item.id && !(item.id in posterLoaded)) {
						posterLoaded[item.id] = false;
					}
				}
			}
		} catch {
			if (controller.signal.aborted) return;
			hasError = true;
			items = [];
		} finally {
			if (searchAbortController === controller) isLoading = false;
		}

		hasSearched = true;
		highlightedIndex = -1;
		isOpen = true;
	}

	function handleInput() {
		clearTimeout(debounceTimer);
		const query = searchTerm.trim();
		if (query.length === 0) {
			searchAbortController?.abort();
			items = [];
			hasSearched = false;
			isOpen = false;
			highlightedIndex = -1;
			hasError = false;
			return;
		}
		debounceTimer = setTimeout(() => runSearch(query), 300);
	}

	function goToSearchPageFor(
		query: string,
		highlight?: { mediaType: CombinedSearchResult['media_type']; id: number }
	) {
		if (query.length === 0) return;
		cancelPendingSearch();
		isOpen = false;
		const params = new SvelteURLSearchParams({ q: query });
		// Lets the search page pick this exact item back out of its results
		// and show it more prominently, since a title match alone could
		// otherwise land on a same-named but different work. The id is a TMDB
		// id: not-in-library suggestions come from the TMDB-sourced title
		// index (see TitleSuggestionService).
		if (highlight) {
			params.set('highlight', `tmdb-${highlight.mediaType}-${highlight.id}`);
		}
		// Refining an already-open search replaces the current history entry
		// instead of pushing a new one, so the search page never piles up
		// multiple entries a "back" button would have to unwind.
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- resolve() result, with a query string appended
		goto(`${resolve('/dashboard/search', {})}?${params.toString()}`, {
			replaceState: isSearchPage(page.url.pathname)
		});
	}

	function goToSearchPage() {
		goToSearchPageFor(searchTerm.trim());
	}

	// Mouse clicks on an in-library row use the row's real `<a href>`, which
	// SvelteKit intercepts natively for client-side navigation - so this
	// only needs to handle the not-in-library case (rendered as a `<button>`
	// with no href to navigate via) and the shared teardown.
	function handleItemClick(item: CombinedSearchResult) {
		clearSearch();
		onResultSelect?.();
		if (!item.in_library && item.external_id != null) {
			goToSearchPageFor(item.name, { mediaType: item.media_type, id: item.external_id });
		}
	}

	// Keyboard selection (Enter) has no native click/anchor event to rely
	// on, so both cases need an explicit navigation.
	function handleItemKeyboardSelect(item: CombinedSearchResult) {
		clearSearch();
		onResultSelect?.();
		if (item.in_library) {
			const href = hrefForItem(item);
			// eslint-disable-next-line svelte/no-navigation-without-resolve -- href is built from resolve() in getMediaTypeHref
			if (href) goto(href);
		} else if (item.external_id != null) {
			goToSearchPageFor(item.name, { mediaType: item.media_type, id: item.external_id });
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'ArrowDown') {
			if (items.length === 0) return;
			e.preventDefault();
			isOpen = true;
			highlightedIndex = (highlightedIndex + 1) % items.length;
		} else if (e.key === 'ArrowUp') {
			if (items.length === 0) return;
			e.preventDefault();
			isOpen = true;
			highlightedIndex = highlightedIndex <= 0 ? items.length - 1 : highlightedIndex - 1;
		} else if (e.key === 'Enter') {
			e.preventDefault();
			const highlighted = items[highlightedIndex];
			if (highlighted) {
				handleItemKeyboardSelect(highlighted);
			} else {
				goToSearchPage();
			}
		} else if (e.key === 'Escape') {
			isOpen = false;
			highlightedIndex = -1;
		}
	}

	function handleFocusOut(e: FocusEvent) {
		const next = e.relatedTarget as Node | null;
		if (!containerRef || !next || !containerRef.contains(next)) {
			isOpen = false;
		}
	}
</script>

<div bind:this={containerRef} class={cn('relative', className)} onfocusout={handleFocusOut}>
	{#if isLoading}
		<LoaderCircle
			class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 animate-spin text-muted-foreground"
		/>
	{:else}
		<Search
			class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
		/>
	{/if}
	<Input
		bind:ref={inputRef}
		bind:value={searchTerm}
		type="search"
		placeholder="Search..."
		class="bg-background pl-9"
		oninput={handleInput}
		onfocus={() => {
			if (hasSearched || items.length > 0) isOpen = true;
		}}
		onkeydown={handleKeydown}
	/>

	{#if isOpen && searchTerm.trim().length > 0}
		<div
			class="absolute top-full z-50 mt-1 w-full rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
		>
			{#if hasError}
				<p class="px-2 py-1.5 text-sm text-destructive">Search failed. Please try again.</p>
			{:else}
				{#snippet rowContent(item: CombinedSearchResult)}
					{@const year = item.year ?? null}
					{#if item.in_library}
						<div class="relative h-12 w-9 shrink-0 overflow-hidden rounded">
							<MediaImage media={{ ...item, year }} bind:loaded={posterLoaded[item.id ?? '']} />
							{#if item.id && !posterLoaded[item.id]}
								<Skeleton class="absolute inset-0 h-full w-full" />
							{/if}
						</div>
					{:else}
						<div class="flex h-12 w-9 shrink-0 items-center justify-center rounded bg-muted">
							<Plus class="size-4 text-muted-foreground" />
						</div>
					{/if}
					<div class="flex min-w-0 flex-col">
						<span class="truncate">
							<span class="font-medium">{item.name}</span>
							{#if year != null && item.media_type === 'movie'}
								<span class="text-muted-foreground">({year})</span>
							{/if}
						</span>
						<span class="flex items-center gap-1 text-xs text-muted-foreground">
							<span class="capitalize">{getMediaTypeLabel(item.media_type)}</span>
							{#if !item.in_library}
								<span aria-hidden="true">&middot;</span>
								<span>Not in library</span>
							{/if}
						</span>
					</div>
				{/snippet}

				{#each items as item, index (itemKey(item))}
					{#if item.in_library}
						<!-- eslint-disable svelte/no-navigation-without-resolve -- href is built from resolve() in getMediaTypeHref -->
						<a
							href={hrefForItem(item)}
							class={rowClass(index)}
							onmouseenter={() => (highlightedIndex = index)}
							onclick={() => handleItemClick(item)}
						>
							<!-- eslint-enable svelte/no-navigation-without-resolve -->
							{@render rowContent(item)}
						</a>
					{:else}
						<button
							type="button"
							class={rowClass(index)}
							onmouseenter={() => (highlightedIndex = index)}
							onclick={() => handleItemClick(item)}
						>
							{@render rowContent(item)}
						</button>
					{/if}
				{:else}
					{#if !isLoading}
						<p class="px-2 py-1.5 text-sm text-muted-foreground">No matching media found.</p>
					{/if}
				{/each}
			{/if}
			<button
				type="button"
				class="w-full rounded-sm border-t px-2 py-1.5 text-left text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
				onmouseenter={() => (highlightedIndex = -1)}
				onclick={goToSearchPage}
			>
				Press <kbd class="rounded border bg-muted px-1 py-0.5 font-mono text-xs">Enter</kbd> to
				search for "{searchTerm.trim()}"
			</button>
		</div>
	{/if}
</div>
