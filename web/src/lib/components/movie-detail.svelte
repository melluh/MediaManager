<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { getCurrentUser, setCrumbs } from '$lib/context.svelte';
	import type { PublicMovie, PublicMovieFile, TorrentWithProgress } from '$lib/api/api';
	import { getFullyQualifiedMediaName, getTorrentStatusString } from '$lib/utils';
	import client from '$lib/api';
	import DownloadTable from '$lib/components/downloads/download-table.svelte';
	import DownloadingButton from '$lib/components/downloads/downloading-button.svelte';
	import MediaHeroHeader from '$lib/components/media-hero-header.svelte';
	import MediaAvailabilityBadge from '$lib/components/media-availability-badge.svelte';
	import MediaActionsMenu from '$lib/components/media-actions-menu.svelte';
	import { movieAvailability } from '$lib/components/movie-availability.js';
	import { withDownloadProgress } from '$lib/components/media-availability.js';
	import DownloadMovieDialog from '$lib/components/download-dialogs/download-movie-dialog.svelte';
	import WatchButton from '$lib/components/watch-button.svelte';
	import MediaFileTable from '$lib/components/media-file-table.svelte';
	import { poll } from '$lib/hooks/poll.svelte';
	import { resolve } from '$app/paths';

	let { movie, movieFiles }: { movie: PublicMovie; movieFiles: PublicMovieFile[] } = $props();
	let hasImportedFile = $derived(movieFiles.some((file) => file.imported));
	let user = getCurrentUser();

	// Polled (rather than fetched once) so a "Downloading" badge's progress bar
	// actually moves while the page is open, matching the dashboard's own
	// downloads carousel, and so the torrent table's status badges stay live
	// too. Progress is only shown for torrents *this* user started - a
	// download started by another admin still shows as "Downloading" without
	// a percentage.
	let movieTorrents: TorrentWithProgress[] = $state([]);
	poll(async () => {
		const { data } = await client.GET('/api/v1/movies/{movie_id}/downloads', {
			params: { path: { movie_id: movie.id! } }
		});
		if (data) movieTorrents = data;
	}, 7000);

	let ownMovieDownloadProgress = $derived(
		movieTorrents.find((t) => t.initiated_by_user_id === user().id)?.download_progress
	);
	let movieAvailabilityInfo = $derived(
		withDownloadProgress(movieAvailability(movie, movieFiles), ownMovieDownloadProgress?.progress)
	);

	// While a torrent is already downloading, the primary action shouldn't
	// invite starting a second one - that's demoted into the overflow menu
	// (mirroring how "Download additional" works once the movie is watchable).
	let isDownloading = $derived(
		(movie.torrents ?? []).some((t) => getTorrentStatusString(t.status) === 'downloading')
	);

	let hasWatchUrl = $state(false);

	setCrumbs(() => [
		{ label: 'Movies', href: resolve('/dashboard/movies', {}) },
		{ label: getFullyQualifiedMediaName(movie) }
	]);
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
						<DownloadingButton progress={ownMovieDownloadProgress} />
					{:else}
						<DownloadMovieDialog {movie} {hasImportedFile} />
					{/if}
				{/snippet}
			</WatchButton>
			<MediaActionsMenu media={movie} isShow={false}>
				{#if hasWatchUrl || isDownloading}
					<DownloadMovieDialog
						{movie}
						{hasImportedFile}
						asMenuItem
						menuLabel="Download additional"
					/>
					<DropdownMenu.Separator />
				{/if}
			</MediaActionsMenu>
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
