<script lang="ts">
	import * as Table from '$lib/components/ui/table/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import type { Episode, PublicEpisodeFile, Season, Show } from '$lib/api/api';
	import { getFullyQualifiedMediaName, getTorrentQualityString } from '$lib/utils';
	import MediaImage from '$lib/components/media-image.svelte';
	import { resolve } from '$app/paths';
	import * as Card from '$lib/components/ui/card/index.js';
	import { getContext } from 'svelte';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';
	import { buttonVariants } from '$lib/components/ui/button/index.js';
	import CheckmarkX from '$lib/components/checkmark-x.svelte';
	import MediaFileDetailsDialog from '$lib/components/media-file-details-dialog.svelte';
	import Info from '@lucide/svelte/icons/info';
	import FileQuestionMark from '@lucide/svelte/icons/file-question-mark';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';

	let { season, episodeFiles }: { season: Season; episodeFiles: PublicEpisodeFile[] } = $props();
	// Provided by the [showId] layout, which resolves it without blocking first paint.
	const getShow: () => Show = getContext('show');
	let show: Show = $derived(getShow());

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	$effect(() => {
		setCrumbs([
			{ label: 'Shows', href: resolve('/dashboard/tv', {}) },
			{
				label: `${show.name} ${show.year == null ? '' : '(' + show.year + ')'}`,
				href: resolve('/dashboard/tv/[showId]', { showId: show.slug! })
			},
			{ label: `Season ${season.number}` }
		]);
	});

	type EpisodeRow = {
		episode: Episode;
		file: PublicEpisodeFile | null;
		fileIndex: number;
		rowSpan: number;
		isFirstForEpisode: boolean;
	};

	// One row per file, with episodes that have no files (or multiple files)
	// represented by 1 or N rows respectively - the episode's own columns are
	// only rendered on the first of those rows and span the rest via rowspan.
	let episodeRows = $derived(
		season.episodes.flatMap((episode): EpisodeRow[] => {
			const files = episodeFiles.filter((file) => file.episode_id === episode.id);
			if (files.length === 0) {
				return [{ episode, file: null, fileIndex: 0, rowSpan: 1, isFirstForEpisode: true }];
			}
			return files.map((file, fileIndex) => ({
				episode,
				file,
				fileIndex,
				rowSpan: files.length,
				isFirstForEpisode: fileIndex === 0
			}));
		})
	);

	// Seasons don't always have their own poster (not every provider/season has
	// one) - fall back to the show's poster, reusing its cache-bust timestamp
	// since season posters are downloaded in the same metadata-refresh pass.
	let seasonPosterMedia = $derived({
		id: season.id,
		name: season.name,
		year: show.year,
		metadata_updated_at: show.metadata_updated_at,
		images: season.images?.poster ? season.images : show.images
	});
</script>

<svelte:head>
	<title>{getFullyQualifiedMediaName(show)} - Season {season.number} - MediaManager</title>
	<meta
		content="View episodes and manage downloads for {getFullyQualifiedMediaName(
			show
		)} Season {season.number} in MediaManager"
		name="description"
	/>
</svelte:head>

<h1 class="scroll-m-20 text-center text-4xl font-extrabold tracking-tight lg:text-5xl">
	{getFullyQualifiedMediaName(show)} - Season {season.number}
</h1>
<main class="mx-auto flex w-full flex-1 flex-col gap-4 p-4 md:max-w-[80em]">
	<div class="flex flex-col gap-4 md:flex-row md:items-stretch">
		<div class="w-full overflow-hidden rounded-xl bg-muted/50 md:w-1/3 md:max-w-sm">
			<MediaImage media={seasonPosterMedia} />
		</div>
		<div class="h-full w-full flex-auto rounded-xl md:w-2/3">
			<Card.Root class="h-full w-full">
				<Card.Content class="flex flex-col gap-6">
					<div>
						<Card.Title class="mb-2 text-base">Series Overview</Card.Title>
						<p class="text-justify text-sm leading-6 hyphens-auto text-muted-foreground">
							{show.overview}
						</p>
					</div>
					<div class="border-t border-border"></div>
					<div>
						<Card.Title class="mb-2 text-base">Season Overview</Card.Title>
						<p class="text-justify text-sm leading-6 hyphens-auto text-muted-foreground">
							{season.overview}
						</p>
					</div>
				</Card.Content>
			</Card.Root>
		</div>
	</div>
	<div class="flex-1 rounded-xl">
		<Card.Root class="w-full">
			<Card.Header>
				<Card.Title>Episodes</Card.Title>
				<Card.Description
					>All episodes for {getFullyQualifiedMediaName(show)} Season {season.number}, with the
					downloaded/downloading file(s) for each.
				</Card.Description>
			</Card.Header>
			<Card.Content class="w-full overflow-x-auto">
				<Table.Root class="w-full table-fixed">
					<Table.Caption>A list of all episodes and their downloaded files.</Table.Caption>
					<Table.Header>
						<Table.Row>
							<Table.Head class="w-[80px]">Number</Table.Head>
							<Table.Head class="w-[200px]">Title</Table.Head>
							<Table.Head>File</Table.Head>
							<Table.Head class="w-[120px]">Quality</Table.Head>
							<Table.Head class="w-[10px]">Imported</Table.Head>
							<Table.Head class="sr-only w-[160px]">Actions</Table.Head>
						</Table.Row>
					</Table.Header>
					<Table.Body>
						{#each episodeRows as row (`${row.episode.id}:${row.fileIndex}`)}
							{@const detailsDialog = row.file
								? shallowDialog(`episodeFileDetails:${row.episode.id}:${row.fileIndex}`)
								: null}
							<Table.Row>
								{#if row.isFirstForEpisode}
									<Table.Cell rowspan={row.rowSpan} class="w-[100px] align-top font-medium">
										E{String(row.episode.number).padStart(2, '0')}
									</Table.Cell>
									<Table.Cell rowspan={row.rowSpan} class="min-w-[50px] align-top">
										{row.episode.title}
									</Table.Cell>
								{/if}
								{#if row.file}
									<Table.Cell class="truncate font-mono text-xs">
										{row.file.relative_path ?? row.file.file_path}
									</Table.Cell>
									<Table.Cell class="w-[120px]">
										{getTorrentQualityString(row.file.quality)}
									</Table.Cell>
									<Table.Cell class="w-[10px] font-medium">
										<CheckmarkX state={row.file.imported} />
									</Table.Cell>
									<Table.Cell class="w-[160px] text-right">
										{#if row.file.downloaded && !row.file.exists_on_disk}
											<span
												class="inline-flex items-center gap-1 text-sm whitespace-nowrap text-muted-foreground"
											>
												<FileQuestionMark class="size-4" />
												Not found on disk
											</span>
										{:else}
											<Dialog.Root
												bind:open={() => detailsDialog!.open, (v) => (detailsDialog!.open = v)}
											>
												<Dialog.Trigger class={buttonVariants({ variant: 'ghost', size: 'sm' })}>
													<Info class="size-4" />
													Details
												</Dialog.Trigger>
												<MediaFileDetailsDialog file={row.file} />
											</Dialog.Root>
										{/if}
									</Table.Cell>
								{:else}
									<Table.Cell colspan={4} class="text-center text-sm text-muted-foreground">
										Not downloaded yet
									</Table.Cell>
								{/if}
							</Table.Row>
						{/each}
					</Table.Body>
				</Table.Root>
			</Card.Content>
		</Card.Root>
	</div>
</main>
