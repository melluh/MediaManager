<script lang="ts">
	import * as Table from '$lib/components/ui/table/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { buttonVariants } from '$lib/components/ui/button/index.js';
	import EllipsisVertical from '@lucide/svelte/icons/ellipsis-vertical';
	import { getContext } from 'svelte';
	import type { PublicMovie, PublicMovieFile, UserRead } from '$lib/api/api';
	import { getFullyQualifiedMediaName, getTorrentQualityString } from '$lib/utils';
	import { page } from '$app/state';
	import TorrentTable from '$lib/components/torrents/torrent-table.svelte';
	import MediaHeroHeader from '$lib/components/media-hero-header.svelte';
	import DownloadMovieDialog from '$lib/components/download-dialogs/download-movie-dialog.svelte';
	import LibraryCombobox from '$lib/components/library-combobox.svelte';
	import { resolve } from '$app/paths';
	import * as Card from '$lib/components/ui/card/index.js';
	import DeleteMediaDialog from '$lib/components/delete-media-dialog.svelte';
	import CheckmarkX from '$lib/components/checkmark-x.svelte';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';

	let movie: PublicMovie = $derived(page.data.movie);
	let movieFiles: PublicMovieFile[] = $derived(page.data.movieFiles);
	let hasImportedFile = $derived(movieFiles.some((file) => file.imported));
	let user: () => UserRead = getContext('user');

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	$effect(() => {
		setCrumbs([
			{ label: 'Movies', href: resolve('/dashboard/movies', {}) },
			{ label: getFullyQualifiedMediaName(movie) }
		]);
	});
</script>

<MediaHeroHeader media={movie} isShow={false}>
	{#snippet actions()}
		{#if user().is_superuser}
			<DownloadMovieDialog {movie} {hasImportedFile} />
			<DropdownMenu.Root>
				<DropdownMenu.Trigger class={buttonVariants({ variant: 'outline', size: 'icon' })}>
					<EllipsisVertical class="size-4" />
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-48">
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
				<Table.Root>
					<Table.Caption>
						A list of all downloaded/downloading versions of this movie.
					</Table.Caption>
					<Table.Header>
						<Table.Row>
							<Table.Head>File Path</Table.Head>
							<Table.Head>Quality</Table.Head>
							<Table.Head>Imported</Table.Head>
						</Table.Row>
					</Table.Header>
					<Table.Body>
						{#each movieFiles as file (file)}
							<Table.Row>
								<Table.Cell class="font-mono text-sm break-all">
									{file.file_path}
								</Table.Cell>
								<Table.Cell class="w-[250px]">
									{getTorrentQualityString(file.quality)}
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
				<TorrentTable isShow={false} torrents={movie.torrents} movieSlug={movie.slug} />
			</Card.Content>
		</Card.Root>
	</div>
</MediaHeroHeader>
