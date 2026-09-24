<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { Button, buttonVariants } from '$lib/components/ui/button/index.js';
	import EllipsisVertical from '@lucide/svelte/icons/ellipsis-vertical';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import Users from '@lucide/svelte/icons/users';
	import Gauge from '@lucide/svelte/icons/gauge';
	import { getContext, onDestroy } from 'svelte';
	import type { PublicMovie, PublicMovieFile, TorrentWithProgress, UserRead } from '$lib/api/api';
	import {
		formatDownloadSpeed,
		getFullyQualifiedMediaName,
		getTorrentStatusString
	} from '$lib/utils';
	import client from '$lib/api';
	import DownloadTable from '$lib/components/downloads/download-table.svelte';
	import MediaHeroHeader from '$lib/components/media-hero-header.svelte';
	import MediaAvailabilityBadge from '$lib/components/media-availability-badge.svelte';
	import { Progress } from '$lib/components/ui/progress/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import { movieAvailability } from '$lib/components/movie-availability.js';
	import { withDownloadProgress } from '$lib/components/media-availability.js';
	import DownloadMovieDialog from '$lib/components/download-dialogs/download-movie-dialog.svelte';
	import LibraryCombobox from '$lib/components/library-combobox.svelte';
	import WatchButton from '$lib/components/watch-button.svelte';
	import { resolve } from '$app/paths';
	import DeleteMediaDialog from '$lib/components/delete-media-dialog.svelte';
	import MediaDetailsDialog from '$lib/components/media-details-dialog.svelte';
	import MediaFileTable from '$lib/components/media-file-table.svelte';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';

	let { movie, movieFiles }: { movie: PublicMovie; movieFiles: PublicMovieFile[] } = $props();
	let hasImportedFile = $derived(movieFiles.some((file) => file.imported));
	let user: () => UserRead = getContext('user');

	// Polled (rather than fetched once) so a "Downloading" badge's progress bar
	// actually moves while the page is open, matching the dashboard's own
	// downloads carousel, and so the torrent table's status badges stay live
	// too. Progress is only shown for torrents *this* user started - a
	// download started by another admin still shows as "Downloading" without
	// a percentage.
	const TORRENTS_POLL_INTERVAL_MS = 7000;
	let movieTorrents: TorrentWithProgress[] = $state([]);
	let movieTorrentsPollHandle: ReturnType<typeof setInterval> | undefined;
	function refreshMovieTorrents() {
		if (document.hidden) return;
		client
			.GET('/api/v1/movies/{movie_id}/downloads', { params: { path: { movie_id: movie.id! } } })
			.then(({ data }) => {
				if (data) movieTorrents = data;
			});
	}
	$effect(() => {
		refreshMovieTorrents();
		movieTorrentsPollHandle = setInterval(refreshMovieTorrents, TORRENTS_POLL_INTERVAL_MS);
	});
	onDestroy(() => clearInterval(movieTorrentsPollHandle));

	let ownMovieDownloadProgress = $derived(
		movieTorrents.find((t) => t.initiated_by_user_id === user().id)?.download_progress
	);
	let movieProgress = $derived(ownMovieDownloadProgress?.progress);
	let movieAvailabilityInfo = $derived(
		withDownloadProgress(movieAvailability(movie, movieFiles), movieProgress)
	);
	let movieDownloadSpeedLabel = $derived(
		formatDownloadSpeed(ownMovieDownloadProgress?.download_speed_bytes_per_second)
	);

	// While a torrent is already downloading, the primary action shouldn't
	// invite starting a second one - that's demoted into the overflow menu
	// (mirroring how "Download additional" works once the movie is watchable).
	let isDownloading = $derived(
		(movie.torrents ?? []).some((t) => getTorrentStatusString(t.status) === 'downloading')
	);

	let hasWatchUrl = $state(false);

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
	{#snippet availability()}
		<MediaAvailabilityBadge availability={movieAvailabilityInfo} />
	{/snippet}
	{#snippet actions()}
		{#if user().is_superuser}
			<WatchButton
				media={movie}
				isShow={false}
				enabled={movie.downloaded}
				bind:available={hasWatchUrl}
			>
				{#snippet fallback()}
					{#if isDownloading}
						<Tooltip.Root disableHoverableContent>
							<Tooltip.Trigger>
								{#snippet child({ props })}
									<span {...props} class="inline-block">
										<Button
											disabled
											class="relative overflow-hidden bg-blue-600 text-white hover:bg-blue-600"
										>
											Downloading{movieProgress != null ? ` ${Math.round(movieProgress)}%` : ''}
											<LoaderCircle class="animate-spin" />
											{#if movieProgress != null}
												<Progress
													value={movieProgress}
													class="absolute inset-x-0 bottom-0 h-1 rounded-none bg-transparent"
												/>
											{/if}
										</Button>
									</span>
								{/snippet}
							</Tooltip.Trigger>
							<Tooltip.Content>
								<div class="flex items-center gap-1.5 whitespace-nowrap">
									<Users class="size-3.5" />
									{ownMovieDownloadProgress?.seeders ?? '?'}
									<span>&middot;</span>
									<Gauge class="size-3.5" />
									{movieDownloadSpeedLabel ?? 'unknown'}
								</div>
							</Tooltip.Content>
						</Tooltip.Root>
					{:else}
						<DownloadMovieDialog {movie} {hasImportedFile} />
					{/if}
				{/snippet}
			</WatchButton>
			<DropdownMenu.Root>
				<DropdownMenu.Trigger class={buttonVariants({ variant: 'outline', size: 'icon' })}>
					<EllipsisVertical class="size-4" />
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-48">
					{#if hasWatchUrl || isDownloading}
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

	<section class="mt-4 flex flex-col gap-3">
		<h2 class="text-lg font-semibold">Files</h2>
		<MediaFileTable
			files={movieFiles}
			leadingLabel="File Path"
			leadingCell={filePathCell}
			emptyMessage="You haven't downloaded this movie yet."
			dialogKeyPrefix="movieFileDetails"
		/>
	</section>
	<section class="mt-4 flex flex-col gap-3">
		<h2 class="text-lg font-semibold">Torrents</h2>
		<DownloadTable torrents={movieTorrents} />
	</section>
</MediaHeroHeader>
