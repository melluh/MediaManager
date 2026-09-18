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
	import type { SearchResult, TitleSuggestion } from '$lib/api/api.d.ts';
	import { cn, getFullyQualifiedMediaName, isSearchPage } from '$lib/utils.js';
	import { getMediaTypeHref, getMediaTypeLabel } from '$lib/media-types.ts';

	type CombinedItem =
		| { kind: 'library'; item: SearchResult }
		| { kind: 'suggestion'; item: TitleSuggestion };

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
	let results: SearchResult[] = $state([]);
	let suggestions: TitleSuggestion[] = $state([]);
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

	// Library results and not-yet-in-library suggestions share one flat list
	// so arrow keys/Enter can move across both sections.
	let combinedItems: CombinedItem[] = $derived([
		...results.map((item): CombinedItem => ({ kind: 'library', item })),
		...suggestions.map((item): CombinedItem => ({ kind: 'suggestion', item }))
	]);

	function hrefForResult(result: SearchResult): string | undefined {
		return getMediaTypeHref(result.media_type, result.slug);
	}

	function cancelPendingSearch() {
		clearTimeout(debounceTimer);
		searchAbortController?.abort();
		isLoading = false;
	}

	function clearSearch() {
		cancelPendingSearch();
		searchTerm = '';
		results = [];
		suggestions = [];
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

		// Library and suggestion results are independent: a `/suggest` failure
		// (e.g. no title index built yet) must not blank library results, and
		// vice versa. `allSettled` (rather than `all`) keeps one from failing
		// the other.
		const [libraryOutcome, suggestOutcome] = await Promise.allSettled([
			client.GET('/api/v1/search', {
				params: { query: { q: query } },
				signal: controller.signal
			}),
			client.GET('/api/v1/search/suggest', {
				params: { query: { q: query } },
				signal: controller.signal
			})
		]);

		if (controller.signal.aborted) return;

		if (libraryOutcome.status === 'fulfilled' && !libraryOutcome.value.error) {
			results = libraryOutcome.value.data ?? [];
			for (const result of results) {
				if (!(result.id in posterLoaded)) posterLoaded[result.id] = false;
			}
		} else {
			hasError = true;
			results = [];
		}

		suggestions =
			suggestOutcome.status === 'fulfilled' && !suggestOutcome.value.error
				? (suggestOutcome.value.data ?? [])
				: [];

		hasSearched = true;
		highlightedIndex = -1;
		isOpen = true;
		isLoading = false;
	}

	function handleInput() {
		clearTimeout(debounceTimer);
		const query = searchTerm.trim();
		if (query.length === 0) {
			searchAbortController?.abort();
			results = [];
			suggestions = [];
			hasSearched = false;
			isOpen = false;
			highlightedIndex = -1;
			hasError = false;
			return;
		}
		debounceTimer = setTimeout(() => runSearch(query), 300);
	}

	function goToSearchPageFor(query: string) {
		if (query.length === 0) return;
		cancelPendingSearch();
		isOpen = false;
		// Refining an already-open search replaces the current history entry
		// instead of pushing a new one, so the search page never piles up
		// multiple entries a "back" button would have to unwind.
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- resolve() result, with a query string appended
		goto(`${resolve('/dashboard/search', {})}?q=${encodeURIComponent(query)}`, {
			replaceState: isSearchPage(page.url.pathname)
		});
	}

	function goToSearchPage() {
		goToSearchPageFor(searchTerm.trim());
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'ArrowDown') {
			if (combinedItems.length === 0) return;
			e.preventDefault();
			isOpen = true;
			highlightedIndex = (highlightedIndex + 1) % combinedItems.length;
		} else if (e.key === 'ArrowUp') {
			if (combinedItems.length === 0) return;
			e.preventDefault();
			isOpen = true;
			highlightedIndex = highlightedIndex <= 0 ? combinedItems.length - 1 : highlightedIndex - 1;
		} else if (e.key === 'Enter') {
			e.preventDefault();
			const highlighted = combinedItems[highlightedIndex];
			if (highlighted?.kind === 'library') {
				const href = hrefForResult(highlighted.item);
				clearSearch();
				onResultSelect?.();
				// eslint-disable-next-line svelte/no-navigation-without-resolve -- href is built from resolve() in getMediaTypeHref
				if (href) goto(href);
			} else if (highlighted?.kind === 'suggestion') {
				const query = highlighted.item.title;
				clearSearch();
				onResultSelect?.();
				goToSearchPageFor(query);
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
			if (hasSearched || combinedItems.length > 0) isOpen = true;
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
				{#each results as result, index (result.id)}
					<!-- eslint-disable svelte/no-navigation-without-resolve -- href is built from resolve() in getMediaTypeHref -->
					<a
						href={hrefForResult(result)}
						class={cn(
							'flex items-center gap-2 rounded-sm px-2 py-1.5 text-sm',
							index === highlightedIndex
								? 'bg-accent text-accent-foreground'
								: 'hover:bg-accent hover:text-accent-foreground'
						)}
						onmouseenter={() => (highlightedIndex = index)}
						onclick={() => {
							clearSearch();
							onResultSelect?.();
						}}
					>
						<!-- eslint-enable svelte/no-navigation-without-resolve -->
						<div class="relative h-12 w-9 shrink-0 overflow-hidden rounded">
							<MediaImage media={result} bind:loaded={posterLoaded[result.id]} />
							{#if !posterLoaded[result.id]}
								<Skeleton class="absolute inset-0 h-full w-full" />
							{/if}
						</div>
						<div class="flex min-w-0 flex-col">
							<span class="truncate font-medium">{getFullyQualifiedMediaName(result)}</span>
							<span class="text-xs text-muted-foreground capitalize">{result.media_type}</span>
						</div>
					</a>
				{/each}
			{/if}

			<!-- Suggestions are fetched independently of the library search
				 (see runSearch) and must keep rendering even if that search
				 failed - so this lives outside the hasError branch above. -->
			{#if suggestions.length > 0}
				<p class="px-2 pt-2 pb-1 text-xs font-medium text-muted-foreground">
					Not in your library yet
				</p>
				{#each suggestions as suggestion, suggestionIndex (`${suggestion.media_type}-${suggestion.id}`)}
					{@const index = results.length + suggestionIndex}
					<button
						type="button"
						class={cn(
							'flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm',
							index === highlightedIndex
								? 'bg-accent text-accent-foreground'
								: 'hover:bg-accent hover:text-accent-foreground'
						)}
						onmouseenter={() => (highlightedIndex = index)}
						onclick={() => {
							const query = suggestion.title;
							clearSearch();
							onResultSelect?.();
							goToSearchPageFor(query);
						}}
					>
						<div class="flex h-12 w-9 shrink-0 items-center justify-center rounded bg-muted">
							<Plus class="size-4 text-muted-foreground" />
						</div>
						<div class="flex min-w-0 flex-col">
							<span class="truncate font-medium">{suggestion.title}</span>
							<span class="text-xs text-muted-foreground">
								{getMediaTypeLabel(suggestion.media_type)}
							</span>
						</div>
					</button>
				{/each}
			{/if}

			{#if combinedItems.length === 0 && !hasError && !isLoading}
				<p class="px-2 py-1.5 text-sm text-muted-foreground">No matching media found.</p>
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
