<script lang="ts">
	import EllipsisVertical from '@lucide/svelte/icons/ellipsis-vertical';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { buttonVariants } from '$lib/components/ui/button/index.js';
	import { getContext, onDestroy } from 'svelte';
	import type { PublicShow, RichShowTorrent, TorrentWithProgress, UserRead } from '$lib/api/api';
	import DownloadSeasonsDialog from '$lib/components/download-dialogs/download-seasons-dialog.svelte';
	import DownloadTable from '$lib/components/downloads/download-table.svelte';
	import MediaHeroHeader from '$lib/components/media-hero-header.svelte';
	import MediaAvailabilityBadge from '$lib/components/media-availability-badge.svelte';
	import { seasonBanner, showAvailability } from '$lib/components/show-availability.js';
	import { withDownloadProgress } from '$lib/components/media-availability.js';
	import * as Carousel from '$lib/components/ui/carousel/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { toast } from 'svelte-sonner';
	import { Label } from '$lib/components/ui/label';
	import LibraryCombobox from '$lib/components/library-combobox.svelte';
	import WatchButton from '$lib/components/watch-button.svelte';
	import DeleteMediaDialog from '$lib/components/delete-media-dialog.svelte';
	import MediaDetailsDialog from '$lib/components/media-details-dialog.svelte';
	import SeasonFilesDialog from '$lib/components/season-files-dialog.svelte';
	import { resolve } from '$app/paths';
	import client from '$lib/api';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';

	// Provided by +layout.svelte, which resolves them without blocking first paint.
	const getShow: () => PublicShow = getContext('show');
	const getTorrents: () => RichShowTorrent = getContext('showTorrents');
	let show: PublicShow = $derived(getShow());
	let torrents: RichShowTorrent = $derived(getTorrents());
	let user: () => UserRead = getContext('user');

	let anyEpisodeDownloaded = $derived(
		show.seasons.some((season) => season.episodes.some((episode) => episode.downloaded))
	);
	let hasWatchUrl = $state(false);

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	$effect(() => {
		setCrumbs([
			{ label: 'Shows', href: resolve('/dashboard/tv', {}) },
			{ label: show.name }
		]);
	});

	// Seasons don't always have their own poster - fall back to the show's,
	// reusing its cache-bust timestamp since season posters are downloaded in
	// the same metadata-refresh pass.
	function seasonPosterMedia(season: PublicShow['seasons'][number]) {
		return {
			id: season.id,
			name: season.name,
			year: show.year,
			metadata_updated_at: show.metadata_updated_at,
			images: season.images?.poster ? season.images : show.images
		};
	}

	// Polled (rather than fetched once) for live progress on whichever season
	// is currently downloading, and so the torrent table's status badges stay
	// live too - same pattern as the movie detail page and the dashboard's
	// downloads carousel.
	const TORRENTS_POLL_INTERVAL_MS = 7000;
	let showTorrentsWithProgress: TorrentWithProgress[] = $state([]);
	let showTorrentsPollHandle: ReturnType<typeof setInterval> | undefined;
	function refreshShowTorrentsWithProgress() {
		if (document.hidden) return;
		client
			.GET('/api/v1/tv/shows/{show_id}/downloads', { params: { path: { show_id: show.id } } })
			.then(({ data }) => {
				if (data) showTorrentsWithProgress = data;
			});
	}
	$effect(() => {
		refreshShowTorrentsWithProgress();
		showTorrentsPollHandle = setInterval(
			refreshShowTorrentsWithProgress,
			TORRENTS_POLL_INTERVAL_MS
		);
	});
	onDestroy(() => clearInterval(showTorrentsPollHandle));

	let showProgress = $derived(
		showTorrentsWithProgress.find((t) => t.initiated_by_user_id === user().id)?.download_progress
			?.progress
	);
	let showAvailabilityInfo = $derived(
		withDownloadProgress(showAvailability(show, torrents.torrents), showProgress)
	);

	let continuousDownloadEnabled = $derived(show.continuous_download);

	async function toggle_continuous_download() {
		const { response } = await client.POST('/api/v1/tv/shows/{show_id}/continuousDownload', {
			params: {
				path: { show_id: show.id },
				query: { continuous_download: !continuousDownloadEnabled }
			}
		});
		console.log(
			'Toggling continuous download for show',
			show.name,
			'to',
			!continuousDownloadEnabled
		);
		if (!response.ok) {
			const errorText = await response.text();
			toast.error('Failed to toggle continuous download: ' + errorText);
		} else {
			continuousDownloadEnabled = !continuousDownloadEnabled;
			toast.success('Continuous download toggled successfully.');
		}
	}
</script>

<MediaHeroHeader media={show} isShow={true}>
	{#snippet availability()}
		<MediaAvailabilityBadge availability={showAvailabilityInfo} />
	{/snippet}
	{#snippet actions()}
		{#if user().is_superuser}
			<WatchButton
				media={show}
				isShow={true}
				enabled={anyEpisodeDownloaded}
				bind:available={hasWatchUrl}
			>
				{#snippet fallback()}
					<DownloadSeasonsDialog {show} />
				{/snippet}
			</WatchButton>
			<DropdownMenu.Root>
				<DropdownMenu.Trigger class={buttonVariants({ variant: 'outline', size: 'icon' })}>
					<EllipsisVertical class="size-4" />
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-64">
					{#if hasWatchUrl}
						<DownloadSeasonsDialog {show} asMenuItem menuLabel="Download additional" />
						<DropdownMenu.Separator />
					{/if}
					{#if !show.ended}
						<div class="flex items-center gap-3 px-2 py-1.5">
							<Switch
								bind:checked={() => continuousDownloadEnabled, toggle_continuous_download}
								id="continuous-download-checkbox"
							/>
							<Label for="continuous-download-checkbox" class="text-xs">
								Enable automatic download of future seasons
							</Label>
						</div>
						<DropdownMenu.Separator />
					{/if}
					<MediaDetailsDialog media={show} isShow={true} />
					<DropdownMenu.Separator />
					<LibraryCombobox media={show} mediaType="tv" />
					<DropdownMenu.Separator />
					<DeleteMediaDialog isShow={true} media={show} />
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		{/if}
	{/snippet}

	{#if show.seasons.length > 0}
		<section class="mt-4 flex flex-col gap-3">
			<h2 class="text-lg font-semibold">Seasons</h2>
			<Carousel.Root class="w-full md:max-[102rem]:px-10" opts={{ align: 'start' }}>
				<Carousel.Content>
					{#each show.seasons as season (season.id)}
						<Carousel.Item class="basis-1/3 sm:basis-1/4 md:basis-1/5 lg:basis-1/7">
							<SeasonFilesDialog
								{show}
								{season}
								posterMedia={seasonPosterMedia(season)}
								banner={seasonBanner(season, torrents.torrents)}
							/>
						</Carousel.Item>
					{/each}
				</Carousel.Content>
				<Carousel.Previous class="left-0 hidden size-9 md:inline-flex min-[102rem]:-left-12" />
				<Carousel.Next class="right-0 hidden size-9 md:inline-flex min-[102rem]:-right-12" />
			</Carousel.Root>
		</section>
	{/if}
	<section class="mt-4 flex flex-col gap-3">
		<h2 class="text-lg font-semibold">Torrents</h2>
		<div class="w-full overflow-x-auto">
			<DownloadTable torrents={showTorrentsWithProgress} />
		</div>
	</section>
</MediaHeroHeader>
