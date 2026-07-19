<script lang="ts">
	import { Separator } from '$lib/components/ui/separator/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import * as Breadcrumb from '$lib/components/ui/breadcrumb/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import AlertCircleIcon from '@lucide/svelte/icons/alert-circle';
	import MediaPicture from '$lib/components/media-picture.svelte';
	import AddMediaCard from '$lib/components/add-media-card.svelte';
	import LoadingBar from '$lib/components/loading-bar.svelte';
	import { getFullyQualifiedMediaName } from '$lib/utils.js';
	import { getMediaTypeHref, getMediaTypeLabel } from '$lib/media-types.ts';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { browser } from '$app/environment';
	import client from '$lib/api';
	import type { SearchResult, MetaDataProviderSearchResult } from '$lib/api/api.d.ts';

	let query = $derived(page.url.searchParams.get('q')?.trim() ?? '');

	const METADATA_PROVIDER_STORAGE_KEY = 'mediamanager:search:metadata-provider';

	function loadStoredMetadataProvider(): 'tmdb' | 'tvdb' {
		if (!browser) return 'tmdb';
		return localStorage.getItem(METADATA_PROVIDER_STORAGE_KEY) === 'tvdb' ? 'tvdb' : 'tmdb';
	}

	let metadataProvider: 'tmdb' | 'tvdb' = $state(loadStoredMetadataProvider());

	$effect(() => {
		if (browser) {
			localStorage.setItem(METADATA_PROVIDER_STORAGE_KEY, metadataProvider);
		}
	});

	let localResults: SearchResult[] = $state([]);
	let localLoading = $state(false);
	let localError = $state(false);

	let externalResults: MetaDataProviderSearchResult[] = $state([]);
	let externalLoading = $state(false);
	let externalError = $state(false);

	// Queries the local database for existing media. Only depends on the
	// query, so switching the metadata provider must not re-trigger this.
	$effect(() => {
		const currentQuery = query;
		if (currentQuery.length === 0) {
			localResults = [];
			localError = false;
			return;
		}

		localLoading = true;
		localError = false;
		client
			.GET('/api/v1/search', { params: { query: { q: currentQuery } } })
			.then(({ data, error }) => {
				if (error) {
					localError = true;
					localResults = [];
				} else {
					localResults = data ?? [];
				}
			})
			.catch(() => {
				localError = true;
				localResults = [];
			})
			.finally(() => {
				localLoading = false;
			});
	});

	// Queries the metadata provider's combined multi-search for new
	// movies/shows to add - a single call ranked by the provider itself
	// (matching e.g. TMDB's own website), rather than stitching together
	// two separately-ranked per-type searches. Re-runs whenever the query
	// or the chosen provider changes, clearing stale results up front so
	// the loading state is shown rather than a stale list.
	$effect(() => {
		const currentQuery = query;
		const currentMetadataProvider = metadataProvider;
		externalResults = [];
		externalError = false;

		if (currentQuery.length === 0) {
			return;
		}

		externalLoading = true;
		client
			.GET('/api/v1/search/external', {
				params: { query: { q: currentQuery, metadata_provider: currentMetadataProvider } }
			})
			.then(({ data, error }) => {
				if (error) {
					externalError = true;
					externalResults = [];
				} else {
					externalResults = data ?? [];
				}
			})
			.catch(() => {
				externalError = true;
				externalResults = [];
			})
			.finally(() => {
				externalLoading = false;
			});
	});
</script>

<svelte:head>
	<title>Search{query ? ` - ${query}` : ''} - MediaManager</title>
	<meta content="Search your MediaManager library and metadata providers" name="description" />
</svelte:head>

<header class="flex h-16 shrink-0 items-center gap-2">
	<div class="flex items-center gap-2 px-4">
		<Sidebar.Trigger class="-ml-1" />
		<Separator class="mr-2 h-4" orientation="vertical" />
		<Breadcrumb.Root>
			<Breadcrumb.List>
				<Breadcrumb.Item class="hidden md:block">
					<Breadcrumb.Link href={resolve('/dashboard', {})}>MediaManager</Breadcrumb.Link>
				</Breadcrumb.Item>
				<Breadcrumb.Separator class="hidden md:block" />
				<Breadcrumb.Item>
					<Breadcrumb.Link href={resolve('/dashboard', {})}>Home</Breadcrumb.Link>
				</Breadcrumb.Item>
				<Breadcrumb.Separator class="hidden md:block" />
				<Breadcrumb.Item>
					<Breadcrumb.Page>Search</Breadcrumb.Page>
				</Breadcrumb.Item>
			</Breadcrumb.List>
		</Breadcrumb.Root>
	</div>
</header>

<main class="flex w-full flex-1 flex-col gap-8 p-4 pt-0">
	<h1 class="scroll-m-20 text-center text-4xl font-extrabold tracking-tight lg:text-5xl">
		{#if query}
			Search results for &quot;{query}&quot;
		{:else}
			Search
		{/if}
	</h1>

	{#if query.length === 0}
		<p class="text-center text-muted-foreground">Enter a search term to get started.</p>
	{:else}
		<section class="flex flex-col gap-4">
			<h2 class="text-2xl font-semibold">In Your Library</h2>
			{#if localLoading}
				<LoadingBar />
			{:else if localError}
				<Alert.Root variant="destructive">
					<AlertCircleIcon class="size-4" />
					<Alert.Title>Search failed</Alert.Title>
					<Alert.Description>Could not search your library. Please try again.</Alert.Description
					>
				</Alert.Root>
			{:else if localResults.length === 0}
				<p class="text-muted-foreground">No matching media in your library.</p>
			{:else}
				<div
					class="grid w-full auto-rows-min gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5"
				>
					{#each localResults as result (result.id)}
						<a href={getMediaTypeHref(result.media_type, result.id)}>
							<Card.Root class="col-span-full max-w-[90vw]">
								<Card.Header>
									<Card.Title class="h-6 truncate">{getFullyQualifiedMediaName(result)}</Card.Title>
									<Card.Description class="truncate">
										{getMediaTypeLabel(result.media_type)} &middot; {result.overview}
									</Card.Description>
								</Card.Header>
								<Card.Content>
									<MediaPicture media={result} />
								</Card.Content>
							</Card.Root>
						</a>
					{/each}
				</div>
			{/if}
		</section>

		<Separator />

		<section class="flex flex-col gap-4">
			<div class="flex items-center justify-between gap-4">
				<h2 class="text-2xl font-semibold">Movies &amp; TV Shows</h2>
				<Select.Root type="single" bind:value={metadataProvider}>
					<Select.Trigger class="w-28">
						{metadataProvider.toUpperCase()}
					</Select.Trigger>
					<Select.Content>
						<Select.Group>
							<Select.GroupHeading>Select the metadata provider to use</Select.GroupHeading>
							<Select.Item value="tmdb" label="TMDB">TMDB</Select.Item>
							<Select.Item value="tvdb" label="TVDB">TVDB</Select.Item>
						</Select.Group>
					</Select.Content>
				</Select.Root>
			</div>
			{#if externalLoading && externalResults.length === 0}
				<LoadingBar />
			{:else if externalError}
				<Alert.Root variant="destructive">
					<AlertCircleIcon class="size-4" />
					<Alert.Title>Search failed</Alert.Title>
					<Alert.Description
						>Could not reach the metadata provider. Please try again later.</Alert.Description
					>
				</Alert.Root>
			{:else if externalResults.length === 0}
				<p class="text-muted-foreground">No movies or TV shows found.</p>
			{:else}
				<div
					class="grid w-full auto-rows-min gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5"
				>
					{#each externalResults as result (`${result.media_type}-${result.external_id}`)}
						<AddMediaCard {result} isShow={result.media_type === 'tv'} />
					{/each}
				</div>
			{/if}
		</section>
	{/if}
</main>
