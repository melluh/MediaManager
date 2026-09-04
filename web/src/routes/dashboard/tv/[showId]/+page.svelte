<script lang="ts">
	import { goto } from '$app/navigation';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import EllipsisVertical from '@lucide/svelte/icons/ellipsis-vertical';
	import * as Table from '$lib/components/ui/table/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { buttonVariants } from '$lib/components/ui/button/index.js';
	import { getContext } from 'svelte';
	import type { PublicShow, RichShowTorrent, UserRead } from '$lib/api/api';
	import { getFullyQualifiedMediaName } from '$lib/utils';
	import DownloadSelectedSeasonsDialog from '$lib/components/download-dialogs/download-selected-seasons-dialog.svelte';
	import DownloadSelectedEpisodesDialog from '$lib/components/download-dialogs/download-selected-episodes-dialog.svelte';
	import DownloadCustomDialog from '$lib/components/download-dialogs/download-custom-dialog.svelte';
	import CheckmarkX from '$lib/components/checkmark-x.svelte';
	import TorrentTable from '$lib/components/torrents/torrent-table.svelte';
	import MediaHeroHeader from '$lib/components/media-hero-header.svelte';
	import MediaImage from '$lib/components/media-image.svelte';
	import * as Carousel from '$lib/components/ui/carousel/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { toast } from 'svelte-sonner';
	import { Label } from '$lib/components/ui/label';
	import LibraryCombobox from '$lib/components/library-combobox.svelte';
	import * as Card from '$lib/components/ui/card/index.js';
	import DeleteMediaDialog from '$lib/components/delete-media-dialog.svelte';
	import { resolve } from '$app/paths';
	import client from '$lib/api';
	import { getTorrentStatusString } from '$lib/utils';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { SvelteSet } from 'svelte/reactivity';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';

	// Provided by +layout.svelte, which resolves them without blocking first paint.
	const getShow: () => PublicShow = getContext('show');
	const getTorrents: () => RichShowTorrent = getContext('showTorrents');
	let show: PublicShow = $derived(getShow());
	let torrents: RichShowTorrent = $derived(getTorrents());
	let user: () => UserRead = getContext('user');

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	$effect(() => {
		setCrumbs([
			{ label: 'Shows', href: resolve('/dashboard/tv', {}) },
			{ label: getFullyQualifiedMediaName(show) }
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

	const seasonBannerClasses = {
		available: 'bg-green-600/90',
		downloading: 'bg-blue-600/90',
		partial: 'bg-amber-600/90',
		missing: 'bg-gray-600/80'
	} as const;

	function seasonBanner(season: PublicShow['seasons'][number]) {
		const total = season.episodes.length;
		const downloadedCount = season.episodes.filter((episode) => episode.downloaded).length;
		const allDownloaded = season.downloaded || (total > 0 && downloadedCount === total);

		if (allDownloaded) {
			return { label: 'Available', classes: seasonBannerClasses.available };
		}

		const isDownloading = torrents.torrents.some(
			(t) => t.seasons.includes(season.number) && getTorrentStatusString(t.status) === 'downloading'
		);
		if (isDownloading) {
			return {
				label: downloadedCount > 0 ? `Downloading (${downloadedCount}/${total})` : 'Downloading',
				classes: seasonBannerClasses.downloading
			};
		}
		if (downloadedCount > 0) {
			return { label: `Partial (${downloadedCount}/${total})`, classes: seasonBannerClasses.partial };
		}
		return { label: 'Missing', classes: seasonBannerClasses.missing };
	}

	let expandedSeasons = $state<Set<string>>(new Set());

	function toggleSeason(seasonId: string) {
		if (expandedSeasons.has(seasonId)) {
			expandedSeasons.delete(seasonId);
		} else {
			expandedSeasons.add(seasonId);
		}
		expandedSeasons = new SvelteSet(expandedSeasons);
	}

	let selectedSeasons = $state<Set<string>>(new Set());

	function toggleSeasonSelection(seasonId: string) {
		if (selectedSeasons.has(seasonId)) {
			selectedSeasons.delete(seasonId);
		} else {
			selectedSeasons.add(seasonId);
		}
		selectedSeasons = new SvelteSet(selectedSeasons);
	}

	let selectedSeasonNumbers = $derived(
		show.seasons.filter((s) => selectedSeasons.has(s.id)).map((s) => s.number)
	);

	let downloadButtonLabel = $derived(
		selectedSeasonNumbers.length === 0
			? 'Download Seasons'
			: `Download Season(s) ${selectedSeasonNumbers
					.slice()
					.sort((a, b) => a - b)
					.map((n) => `S${String(n).padStart(2, '0')}`)
					.join(', ')}`
	);

	let selectedEpisodes = $state<Set<string>>(new Set());

	function toggleEpisodeSelection(episodeId: string) {
		if (selectedEpisodes.has(episodeId)) {
			selectedEpisodes.delete(episodeId);
		} else {
			selectedEpisodes.add(episodeId);
		}
		selectedEpisodes = new SvelteSet(selectedEpisodes);
	}

	let selectedEpisodeNumbers = $derived(
		show.seasons.flatMap((season) =>
			season.episodes
				.filter((ep) => selectedEpisodes.has(ep.id))
				.map((ep) => ({
					seasonNumber: season.number,
					episodeNumber: ep.number
				}))
		)
	);

	let episodeDownloadLabel = $derived(
		selectedEpisodeNumbers.length === 0
			? 'Download Episodes'
			: `Download Episode(s) ${selectedEpisodeNumbers
					.map(
						(e) =>
							`S${String(e.seasonNumber).padStart(2, '0')}E${String(e.episodeNumber).padStart(
								2,
								'0'
							)}`
					)
					.join(', ')}`
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
	{#snippet actions()}
		{#if user().is_superuser}
			{#if selectedSeasonNumbers.length > 0}
				<DownloadSelectedSeasonsDialog
					{show}
					{selectedSeasonNumbers}
					triggerText={downloadButtonLabel}
				/>
			{/if}
			{#if selectedEpisodeNumbers.length > 0}
				<DownloadSelectedEpisodesDialog
					{show}
					{selectedEpisodeNumbers}
					triggerText={episodeDownloadLabel}
				/>
			{/if}
			{#if selectedSeasonNumbers.length === 0 && selectedEpisodeNumbers.length === 0}
				<DownloadCustomDialog {show} />
			{/if}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger class={buttonVariants({ variant: 'outline', size: 'icon' })}>
					<EllipsisVertical class="size-4" />
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-64">
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
					<LibraryCombobox media={show} mediaType="tv" />
					<DropdownMenu.Separator />
					<DeleteMediaDialog isShow={true} media={show} />
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		{/if}
	{/snippet}

	{#if show.seasons.length > 0}
		<div class="flex-1 rounded-xl">
			<Card.Root class="w-full">
				<Card.Header>
					<Card.Title>Seasons</Card.Title>
				</Card.Header>
				<Card.Content>
					<Carousel.Root class="w-full md:px-10" opts={{ align: 'start' }}>
						<Carousel.Content>
							{#each show.seasons as season (season.id)}
								{@const banner = seasonBanner(season)}
								<Carousel.Item class="basis-1/3 sm:basis-1/4 md:basis-1/5 lg:basis-1/6">
									<a
										href={resolve('/dashboard/tv/[showId]/[seasonId]', {
											showId: show.slug,
											seasonId: season.id
										})}
										class="group relative block aspect-2/3 w-full overflow-hidden rounded-lg bg-muted/50 ring-1 ring-border transition-shadow hover:shadow-lg"
									>
										<MediaImage
											media={seasonPosterMedia(season)}
											className="h-full w-full object-cover transition-transform duration-200 group-hover:scale-105"
											loading="lazy"
										/>
										<div
											class="absolute inset-0 flex flex-col justify-end gap-0.5 bg-gradient-to-t from-black/90 via-black/40 to-transparent p-2 pb-6 text-white"
										>
											<p class="text-sm leading-tight font-semibold">
												{season.name}
											</p>
											<p class="truncate text-xs text-white/70">
												{season.episodes.length} episodes
											</p>
										</div>
										<div
											class={`absolute inset-x-0 bottom-0 z-10 py-1 text-center text-[10px] font-semibold tracking-wide text-white ${banner.classes}`}
										>
											{banner.label}
										</div>
									</a>
								</Carousel.Item>
							{/each}
						</Carousel.Content>
						<Carousel.Previous class="left-0 hidden size-9 md:inline-flex" />
						<Carousel.Next class="right-0 hidden size-9 md:inline-flex" />
					</Carousel.Root>
				</Card.Content>
			</Card.Root>
		</div>
	{/if}
	<div class="flex-1 rounded-xl">
		<Card.Root class="w-full">
			<Card.Header>
				<Card.Title>Season Details</Card.Title>
				<Card.Description>
					A list of all seasons for {getFullyQualifiedMediaName(show)}.
				</Card.Description>
			</Card.Header>
			<Card.Content class="w-full overflow-x-auto">
				<Table.Root class="w-full table-fixed">
					<Table.Caption>A list of all seasons.</Table.Caption>
					<Table.Header>
						<Table.Row>
							<Table.Head class="w-[40px]"></Table.Head>
							<Table.Head class="w-[80px]">Number</Table.Head>
							<Table.Head class="w-[100px]">Exists on disk</Table.Head>
							<Table.Head class="w-[240px]">Title</Table.Head>
							<Table.Head>Overview</Table.Head>
							<Table.Head class="w-[64px] text-center">Details</Table.Head>
						</Table.Row>
					</Table.Header>
					<Table.Body>
						{#if show.seasons.length > 0}
							{#each show.seasons as season (season.id)}
								<Table.Row
									class={`group cursor-pointer transition-colors hover:bg-muted/60 ${
										expandedSeasons.has(season.id) ? 'bg-muted/50' : 'bg-muted/10'
									}`}
									onclick={() => toggleSeason(season.id)}
								>
									<Table.Cell class="w-[40px]">
										<Checkbox
											checked={selectedSeasons.has(season.id)}
											onCheckedChange={() => toggleSeasonSelection(season.id)}
											onclick={(e) => e.stopPropagation()}
										/>
									</Table.Cell>
									<Table.Cell class="min-w-[10px] font-medium">
										S{String(season.number).padStart(2, '0')}
									</Table.Cell>
									<Table.Cell class="min-w-[10px] font-medium">
										<CheckmarkX state={season.downloaded} />
									</Table.Cell>
									<Table.Cell class="min-w-[50px]">{season.name}</Table.Cell>
									<Table.Cell class="max-w-[300px] truncate">{season.overview}</Table.Cell>
									<Table.Cell class="w-[64px] text-center">
										<button
											class="inline-flex cursor-pointer items-center
												justify-center
												rounded-md p-1
												transition-colors
												hover:bg-muted/95
												focus-visible:ring-2
												focus-visible:ring-ring focus-visible:outline-none"
											onclick={(e) => {
												e.stopPropagation();
												goto(
													resolve('/dashboard/tv/[showId]/[seasonId]', {
														showId: show.slug,
														seasonId: season.id
													})
												);
											}}
											aria-label="Season details"
										>
											<Ellipsis size={16} class="text-muted-foreground" />
										</button>
									</Table.Cell>
								</Table.Row>
								{#if expandedSeasons.has(season.id)}
									{#each season.episodes as episode (episode.id)}
										<Table.Row class="bg-muted/20">
											<Table.Cell class="w-[40px]">
												<Checkbox
													checked={selectedEpisodes.has(episode.id)}
													onCheckedChange={() => toggleEpisodeSelection(episode.id)}
													onclick={(e) => e.stopPropagation()}
												/>
											</Table.Cell>
											<Table.Cell class="min-w-[10px] font-medium">
												E{String(episode.number).padStart(2, '0')}
											</Table.Cell>
											<Table.Cell class="min-w-[10px] font-medium">
												<CheckmarkX state={episode.downloaded} />
											</Table.Cell>
											<Table.Cell class="min-w-[50px]">{episode.title}</Table.Cell>
											<Table.Cell colspan={2} class="truncate">{episode.overview}</Table.Cell>
										</Table.Row>
									{/each}
								{/if}
							{/each}
						{:else}
							<Table.Row>
								<Table.Cell colspan={3} class="text-center">No season data available.</Table.Cell>
							</Table.Row>
						{/if}
					</Table.Body>
				</Table.Root>
			</Card.Content>
		</Card.Root>
	</div>
	<div class="flex-1 rounded-xl">
		<Card.Root>
			<Card.Header>
				<Card.Title>Torrent Information</Card.Title>
				<Card.Description>A list of all torrents associated with this show.</Card.Description>
			</Card.Header>

			<Card.Content class="w-full overflow-x-auto">
				<TorrentTable isShow={true} torrents={torrents.torrents} showSlug={show.slug} />
			</Card.Content>
		</Card.Root>
	</div>
</MediaHeroHeader>
