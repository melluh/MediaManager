<script lang="ts">
	import { goto } from '$app/navigation';
	import { ImageOff } from 'lucide-svelte';
	import { Ellipsis } from 'lucide-svelte';
	import { ChevronDown } from 'lucide-svelte';
	import * as Table from '$lib/components/ui/table/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { buttonVariants } from '$lib/components/ui/button/index.js';
	import { getContext } from 'svelte';
	import type { PublicShow, RichShowTorrent, UserRead } from '$lib/api/api';
	import {
		getFullyQualifiedMediaName,
		formatRuntime,
		formatReleaseDate,
		formatLastUpdated,
		getMetadataProviderLabel,
		getMetadataProviderUrl
	} from '$lib/utils';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import DownloadSelectedSeasonsDialog from '$lib/components/download-dialogs/download-selected-seasons-dialog.svelte';
	import DownloadSelectedEpisodesDialog from '$lib/components/download-dialogs/download-selected-episodes-dialog.svelte';
	import DownloadCustomDialog from '$lib/components/download-dialogs/download-custom-dialog.svelte';
	import CheckmarkX from '$lib/components/checkmark-x.svelte';
	import { page } from '$app/state';
	import TorrentTable from '$lib/components/torrents/torrent-table.svelte';
	import MediaPicture from '$lib/components/media-picture.svelte';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { toast } from 'svelte-sonner';
	import { Label } from '$lib/components/ui/label';
	import LibraryCombobox from '$lib/components/library-combobox.svelte';
	import * as Card from '$lib/components/ui/card/index.js';
	import DeleteMediaDialog from '$lib/components/delete-media-dialog.svelte';
	import { resolve } from '$app/paths';
	import client from '$lib/api';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { SvelteSet } from 'svelte/reactivity';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';

	let show: PublicShow = $derived(page.data.showData);
	let torrents: RichShowTorrent = $derived(page.data.torrentsData);
	let user: () => UserRead = getContext('user');

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	$effect(() => {
		setCrumbs([
			{ label: 'Shows', href: resolve('/dashboard/tv', {}) },
			{ label: getFullyQualifiedMediaName(show) }
		]);
	});

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

<svelte:head>
	<title>{getFullyQualifiedMediaName(show)} - MediaManager</title>
	<meta
		content="View details and manage downloads for {getFullyQualifiedMediaName(
			show
		)} in MediaManager"
		name="description"
	/>
</svelte:head>

<div class="mx-auto mb-4 w-full px-4 md:max-w-[80em]">
	<h1 class="scroll-m-20 text-left text-4xl font-extrabold tracking-tight lg:text-5xl">
		{getFullyQualifiedMediaName(show)}
	</h1>
</div>
<main class="mx-auto flex w-full flex-1 flex-col gap-4 p-4 md:max-w-[80em]">
	<div class="flex flex-col gap-4 md:flex-row md:items-stretch">
		<div class="w-full overflow-hidden rounded-xl bg-muted/50 md:w-1/3 md:max-w-sm">
			{#if show.id}
				<MediaPicture media={show} />
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
						{#if show.tagline}
							<p class="text-sm italic text-muted-foreground">"{show.tagline}"</p>
						{/if}
						<div class="flex flex-wrap items-center gap-x-3 gap-y-2 text-sm text-muted-foreground">
							{#if formatReleaseDate(show.release_date)}
								<span>{formatReleaseDate(show.release_date)}</span>
							{/if}
							{#if formatRuntime(show.runtime)}
								<span>{formatRuntime(show.runtime)}</span>
							{/if}
							{#if show.genres && show.genres.length > 0}
								<div class="flex flex-wrap gap-1">
									{#each show.genres as genre (genre)}
										<Badge variant="secondary">{genre}</Badge>
									{/each}
								</div>
							{/if}
						</div>
						<p class="text-justify text-sm leading-6 hyphens-auto text-muted-foreground">
							{show.overview}
						</p>
						{#if getMetadataProviderUrl(show.metadata_provider, show.external_id, true)}
							<p class="text-xs text-muted-foreground">
								Source:
								<a
									href={getMetadataProviderUrl(show.metadata_provider, show.external_id, true)}
									target="_blank"
									rel="noopener noreferrer"
									class="underline hover:text-foreground"
								>
									{getMetadataProviderLabel(show.metadata_provider)}
								</a>
								{#if formatLastUpdated(show.metadata_updated_at)}
									· Last updated: {formatLastUpdated(show.metadata_updated_at)}
								{/if}
							</p>
						{/if}
					</div>
					{#if user().is_superuser}
						<div class="flex items-center justify-between gap-2">
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
								<DropdownMenu.Trigger class={buttonVariants({ variant: 'outline' })}>
									Administrator Actions
									<ChevronDown />
								</DropdownMenu.Trigger>
								<DropdownMenu.Content align="end" class="flex w-56 flex-col gap-2 p-3">
									{#if !show.ended}
										<div class="flex items-center gap-3 px-1 py-1">
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
									<DeleteMediaDialog isShow={true} media={show} />
								</DropdownMenu.Content>
							</DropdownMenu.Root>
						</div>
					{/if}
				</Card.Content>
			</Card.Root>
		</div>
	</div>
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
														showId: show.id,
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
				<TorrentTable isShow={true} torrents={torrents.torrents} showId={show.id} />
			</Card.Content>
		</Card.Root>
	</div>
</main>
