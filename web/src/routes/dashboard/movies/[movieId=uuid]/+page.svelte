<script lang="ts">
	import * as Table from '$lib/components/ui/table/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { buttonVariants } from '$lib/components/ui/button/index.js';
	import { ImageOff, ChevronDown } from 'lucide-svelte';
	import { getContext } from 'svelte';
	import type { PublicMovie, PublicMovieFile, UserRead } from '$lib/api/api';
	import {
		getFullyQualifiedMediaName,
		getTorrentQualityString,
		formatRuntime,
		formatReleaseDate,
		formatLastUpdated,
		getMetadataProviderLabel,
		getMetadataProviderUrl
	} from '$lib/utils';
	import { page } from '$app/state';
	import TorrentTable from '$lib/components/torrents/torrent-table.svelte';
	import MediaPicture from '$lib/components/media-picture.svelte';
	import DownloadMovieDialog from '$lib/components/download-dialogs/download-movie-dialog.svelte';
	import LibraryCombobox from '$lib/components/library-combobox.svelte';
	import { resolve } from '$app/paths';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import DeleteMediaDialog from '$lib/components/delete-media-dialog.svelte';
	import CheckmarkX from '$lib/components/checkmark-x.svelte';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';

	let movie: PublicMovie = $derived(page.data.movie);
	let movieFiles: PublicMovieFile[] = $derived(page.data.movieFiles);
	let user: () => UserRead = getContext('user');

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	$effect(() => {
		setCrumbs([
			{ label: 'Movies', href: resolve('/dashboard/movies', {}) },
			{ label: getFullyQualifiedMediaName(movie) }
		]);
	});
</script>

<svelte:head>
	<title>{getFullyQualifiedMediaName(movie)} - MediaManager</title>
	<meta
		content="View details and manage downloads for {getFullyQualifiedMediaName(
			movie
		)} in MediaManager"
		name="description"
	/>
</svelte:head>

<div class="mx-auto mb-4 w-full px-4 md:max-w-[80em]">
	<h1 class="scroll-m-20 text-left text-4xl font-extrabold tracking-tight lg:text-5xl">
		{getFullyQualifiedMediaName(movie)}
	</h1>
</div>
<main class="mx-auto flex w-full flex-1 flex-col gap-4 p-4 md:max-w-[80em]">
	<div class="flex flex-col gap-4 md:flex-row md:items-stretch">
		<div class="w-full overflow-hidden rounded-xl bg-muted/50 md:w-1/3 md:max-w-sm">
			{#if movie.id}
				<MediaPicture media={movie} />
			{:else}
				<div
					class="flex aspect-9/16 h-auto w-full items-center justify-center rounded-lg bg-gray-200 text-gray-500"
				>
					<ImageOff size={48} />
				</div>
			{/if}
		</div>
		<div class="flex h-full w-full flex-auto flex-col rounded-xl md:flex-1">
			<Card.Root class="flex h-full w-full flex-col">
				<Card.Header>
					<Card.Title>Overview</Card.Title>
				</Card.Header>
				<Card.Content class="flex flex-1 flex-col justify-between gap-4">
					<div class="flex flex-col gap-3">
						{#if movie.tagline}
							<p class="text-sm italic text-muted-foreground">"{movie.tagline}"</p>
						{/if}
						<div class="flex flex-wrap items-center gap-x-3 gap-y-2 text-sm text-muted-foreground">
							{#if formatReleaseDate(movie.release_date)}
								<span>{formatReleaseDate(movie.release_date)}</span>
							{/if}
							{#if formatRuntime(movie.runtime)}
								<span>{formatRuntime(movie.runtime)}</span>
							{/if}
							{#if movie.genres && movie.genres.length > 0}
								<div class="flex flex-wrap gap-1">
									{#each movie.genres as genre (genre)}
										<Badge variant="secondary">{genre}</Badge>
									{/each}
								</div>
							{/if}
						</div>
						<p class="text-justify text-sm leading-6 hyphens-auto text-muted-foreground">
							{movie.overview}
						</p>
						{#if getMetadataProviderUrl(movie.metadata_provider, movie.external_id, false)}
							<p class="text-xs text-muted-foreground">
								Source:
								<a
									href={getMetadataProviderUrl(movie.metadata_provider, movie.external_id, false)}
									target="_blank"
									rel="noopener noreferrer"
									class="underline hover:text-foreground"
								>
									{getMetadataProviderLabel(movie.metadata_provider)}
								</a>
								{#if formatLastUpdated(movie.metadata_updated_at)}
									· Last updated: {formatLastUpdated(movie.metadata_updated_at)}
								{/if}
							</p>
						{/if}
					</div>
					{#if user().is_superuser}
						<div class="flex items-center justify-between gap-2">
							<DownloadMovieDialog {movie} />
							<DropdownMenu.Root>
								<DropdownMenu.Trigger class={buttonVariants({ variant: 'outline' })}>
									Administrator Actions
									<ChevronDown />
								</DropdownMenu.Trigger>
								<DropdownMenu.Content align="end" class="flex w-56 flex-col gap-2 p-3">
									<LibraryCombobox media={movie} mediaType="movie" />
									<DeleteMediaDialog isShow={false} media={movie} />
								</DropdownMenu.Content>
							</DropdownMenu.Root>
						</div>
					{/if}
				</Card.Content>
			</Card.Root>
		</div>
	</div>
	<div class="flex-1 rounded-xl">
		<Card.Root class="h-full w-full">
			<Card.Header>
				<Card.Title>Movie files</Card.Title>
				<Card.Description>
					A list of all downloaded/downloading versions of this movie.
				</Card.Description>
			</Card.Header>
			<Card.Content>
				<Table.Root>
					<Table.Caption>
						A list of all downloaded/downloading versions of this movie.
					</Table.Caption>
					<Table.Header>
						<Table.Row>
							<Table.Head>Quality</Table.Head>
							<Table.Head>File Path Suffix</Table.Head>
							<Table.Head>Imported</Table.Head>
						</Table.Row>
					</Table.Header>
					<Table.Body>
						{#each movieFiles as file (file)}
							<Table.Row>
								<Table.Cell class="w-[50px]">
									{getTorrentQualityString(file.quality)}
								</Table.Cell>
								<Table.Cell class="w-[100px]">
									{file.file_path_suffix}
								</Table.Cell>
								<Table.Cell class="w-[10px] font-medium">
									<CheckmarkX state={file.imported} />
								</Table.Cell>
							</Table.Row>
						{/each}
					</Table.Body>
				</Table.Root>
			</Card.Content>
		</Card.Root>
	</div>
	<div class="flex-1 rounded-xl">
		<Card.Root class="h-full w-full">
			<Card.Header>
				<Card.Title>Torrent Information</Card.Title>
				<Card.Description>A list of all torrents associated with this movie.</Card.Description>
			</Card.Header>
			<Card.Content class="flex flex-col gap-4">
				<TorrentTable isShow={false} torrents={movie.torrents} movieId={movie.id} />
			</Card.Content>
		</Card.Root>
	</div>
</main>
