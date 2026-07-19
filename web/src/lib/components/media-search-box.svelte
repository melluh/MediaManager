<script lang="ts">
	import { Input } from '$lib/components/ui/input/index.js';
	import MediaPicture from '$lib/components/media-picture.svelte';
	import { Search, LoaderCircle } from 'lucide-svelte';
	import { resolve } from '$app/paths';
	import { goto } from '$app/navigation';
	import client from '$lib/api';
	import type { SearchResult } from '$lib/api/api.d.ts';
	import { cn, getFullyQualifiedMediaName } from '$lib/utils.js';
	import { getMediaTypeHref } from '$lib/media-types.ts';

	let { class: className = '' }: { class?: string } = $props();

	let searchTerm = $state('');
	let results: SearchResult[] = $state([]);
	let isOpen = $state(false);
	let isLoading = $state(false);
	let hasError = $state(false);
	let highlightedIndex = $state(-1);
	let containerRef: HTMLDivElement | undefined = $state();
	let debounceTimer: ReturnType<typeof setTimeout> | undefined;

	function hrefForResult(result: SearchResult): string | undefined {
		return getMediaTypeHref(result.media_type, result.id);
	}

	async function runSearch(query: string) {
		isLoading = true;
		hasError = false;
		try {
			const { data, error } = await client.GET('/api/v1/search', {
				params: { query: { q: query } }
			});
			if (error) {
				hasError = true;
				results = [];
			} else {
				results = data ?? [];
			}
			highlightedIndex = -1;
			isOpen = true;
		} catch {
			hasError = true;
			results = [];
			isOpen = true;
		} finally {
			isLoading = false;
		}
	}

	function handleInput() {
		clearTimeout(debounceTimer);
		const query = searchTerm.trim();
		if (query.length === 0) {
			results = [];
			isOpen = false;
			highlightedIndex = -1;
			hasError = false;
			return;
		}
		debounceTimer = setTimeout(() => runSearch(query), 300);
	}

	function goToSearchPage() {
		const query = searchTerm.trim();
		if (query.length === 0) return;
		isOpen = false;
		goto(`${resolve('/dashboard/search', {})}?q=${encodeURIComponent(query)}`);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'ArrowDown') {
			if (results.length === 0) return;
			e.preventDefault();
			isOpen = true;
			highlightedIndex = (highlightedIndex + 1) % results.length;
		} else if (e.key === 'ArrowUp') {
			if (results.length === 0) return;
			e.preventDefault();
			isOpen = true;
			highlightedIndex = highlightedIndex <= 0 ? results.length - 1 : highlightedIndex - 1;
		} else if (e.key === 'Enter') {
			e.preventDefault();
			const highlighted = results[highlightedIndex];
			if (highlighted) {
				const href = hrefForResult(highlighted);
				isOpen = false;
				if (href) goto(href);
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
		bind:value={searchTerm}
		type="search"
		placeholder="Search..."
		class="pl-9"
		oninput={handleInput}
		onfocus={() => {
			if (results.length > 0) isOpen = true;
		}}
		onkeydown={handleKeydown}
	/>

	{#if isOpen && searchTerm.trim().length > 0}
		<div
			class="absolute top-full z-50 mt-1 w-full rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
		>
			{#if hasError}
				<p class="px-2 py-1.5 text-sm text-destructive">
					Search failed. Please try again.
				</p>
			{:else}
				{#each results as result, index (result.id)}
					<a
						href={hrefForResult(result)}
						class={cn(
							'flex items-center gap-2 rounded-sm px-2 py-1.5 text-sm',
							index === highlightedIndex
								? 'bg-accent text-accent-foreground'
								: 'hover:bg-accent hover:text-accent-foreground'
						)}
						onmouseenter={() => (highlightedIndex = index)}
						onclick={() => (isOpen = false)}
					>
						<div class="h-12 w-9 shrink-0 overflow-hidden rounded">
							<MediaPicture media={result} />
						</div>
						<div class="flex min-w-0 flex-col">
							<span class="truncate font-medium">{getFullyQualifiedMediaName(result)}</span>
							<span class="text-xs text-muted-foreground capitalize">{result.media_type}</span>
						</div>
					</a>
				{:else}
					{#if !isLoading}
						<p class="px-2 py-1.5 text-sm text-muted-foreground">
							No matching media in your library.
						</p>
					{/if}
				{/each}
			{/if}
			<button
				type="button"
				class="w-full rounded-sm border-t px-2 py-1.5 text-left text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
				onmouseenter={() => (highlightedIndex = -1)}
				onclick={goToSearchPage}
			>
				Press <kbd class="rounded border bg-muted px-1 py-0.5 font-mono text-xs">Enter</kbd> to search
				for "{searchTerm.trim()}"
			</button>
		</div>
	{/if}
</div>
