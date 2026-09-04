<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { Button, buttonVariants } from '$lib/components/ui/button/index.js';
	import EllipsisVertical from '@lucide/svelte/icons/ellipsis-vertical';
	import Play from '@lucide/svelte/icons/play';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import { getContext } from 'svelte';
	import type { PublicMovie, PublicMovieFile, UserRead } from '$lib/api/api';
	import { getFullyQualifiedMediaName } from '$lib/utils';
	import client from '$lib/api';
	import TorrentTable from '$lib/components/torrents/torrent-table.svelte';
	import MediaHeroHeader from '$lib/components/media-hero-header.svelte';
	import DownloadMovieDialog from '$lib/components/download-dialogs/download-movie-dialog.svelte';
	import LibraryCombobox from '$lib/components/library-combobox.svelte';
	import { resolve } from '$app/paths';
	import * as Card from '$lib/components/ui/card/index.js';
	import DeleteMediaDialog from '$lib/components/delete-media-dialog.svelte';
	import MediaDetailsDialog from '$lib/components/media-details-dialog.svelte';
	import MediaFileTable from '$lib/components/media-file-table.svelte';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';

	let { movie, movieFiles }: { movie: PublicMovie; movieFiles: PublicMovieFile[] } = $props();
	let hasImportedFile = $derived(movieFiles.some((file) => file.imported));
	let user: () => UserRead = getContext('user');

	// Fetched separately from the movie's own details so a slow/unconfigured
	// media server never blocks the movie page from loading.
	let watchUrl: string | null = $state(null);
	let watchMediaServerName: string | null = $state(null);
	let watchUrlLoading = $state(false);
	$effect(() => {
		watchUrl = null;
		watchMediaServerName = null;
		if (!movie.downloaded) return;
		watchUrlLoading = true;
		client
			.GET('/api/v1/movies/{movie_id}/watch-url', { params: { path: { movie_id: movie.id! } } })
			.then(({ data }) => {
				watchUrl = data?.url ?? null;
				watchMediaServerName = data?.media_server_name ?? null;
			})
			.finally(() => {
				watchUrlLoading = false;
			});
	});

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	$effect(() => {
		setCrumbs([
			{ label: 'Movies', href: resolve('/dashboard/movies', {}) },
			{ label: getFullyQualifiedMediaName(movie) }
		]);
	});
</script>

{#snippet filePathCell(file: PublicMovieFile)}
	<span class="font-mono text-sm break-all">{file.file_path}</span>
{/snippet}

<MediaHeroHeader media={movie} isShow={false}>
	{#snippet actions()}
		{#if user().is_superuser}
			{#if movie.downloaded && watchUrlLoading}
				<Button disabled class="bg-green-600 text-white hover:bg-green-700">
					Watch
					<LoaderCircle class="animate-spin" />
				</Button>
			{:else if watchUrl}
				<Button
					href={watchUrl}
					target="_blank"
					rel="noopener noreferrer"
					class="bg-green-600 text-white hover:bg-green-700"
				>
					Watch on {watchMediaServerName}
					<Play />
				</Button>
			{:else}
				<DownloadMovieDialog {movie} {hasImportedFile} />
			{/if}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger class={buttonVariants({ variant: 'outline', size: 'icon' })}>
					<EllipsisVertical class="size-4" />
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-48">
					{#if watchUrl}
						<DownloadMovieDialog
							{movie}
							{hasImportedFile}
							asMenuItem
							menuLabel="Download additional"
						/>
						<DropdownMenu.Separator />
					{/if}
					<MediaDetailsDialog media={movie} isShow={false} />
					<DropdownMenu.Separator />
					<LibraryCombobox media={movie} mediaType="movie" />
					<DropdownMenu.Separator />
					<DeleteMediaDialog isShow={false} media={movie} />
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		{/if}
	{/snippet}

	<div class="flex-1 rounded-xl">
		<Card.Root class="h-full w-full">
			<Card.Header>
				<Card.Title>Movie files</Card.Title>
				<Card.Description>
					A list of all downloaded/downloading versions of this movie.
				</Card.Description>
			</Card.Header>
			<Card.Content>
				<MediaFileTable
					files={movieFiles}
					caption="A list of all downloaded/downloading versions of this movie."
					leadingLabel="File Path"
					leadingCell={filePathCell}
					emptyMessage="You haven't downloaded this movie yet."
					dialogKeyPrefix="movieFileDetails"
				/>
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
				<TorrentTable isShow={false} torrents={movie.torrents ?? []} movieSlug={movie.slug} />
			</Card.Content>
		</Card.Root>
	</div>
</MediaHeroHeader>
