<script lang="ts">
	import * as Table from '$lib/components/ui/table/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import { buttonVariants } from '$lib/components/ui/button/index.js';
	import type { PublicEpisodeFile, PublicShow } from '$lib/api/api';
	import { getFullyQualifiedMediaName, getTorrentQualityString } from '$lib/utils';
	import MediaImage from '$lib/components/media-image.svelte';
	import CheckmarkX from '$lib/components/checkmark-x.svelte';
	import MediaFileDetailsDialog from '$lib/components/media-file-details-dialog.svelte';
	import Info from '@lucide/svelte/icons/info';
	import FileQuestionMark from '@lucide/svelte/icons/file-question-mark';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';
	import { untrack } from 'svelte';
	import client from '$lib/api';

	type Season = PublicShow['seasons'][number];

	let {
		show,
		season,
		posterMedia,
		banner
	}: {
		show: PublicShow;
		season: Season;
		posterMedia: {
			id: string;
			name: string;
			year: number | null;
			metadata_updated_at?: string | null;
			images?: Record<string, string>;
		};
		banner: { label: string; classes: string };
	} = $props();

	const dialogState = shallowDialog(`seasonFiles:${season.id}`);

	let episodeFiles = $state<PublicEpisodeFile[] | null>(null);
	let loading = $state(false);

	$effect(() => {
		const open = dialogState.open;
		if (!open) {
			untrack(() => {
				episodeFiles = null;
			});
			return;
		}
		loading = true;
		client
			.GET('/api/v1/tv/seasons/{season_id}/files', {
				params: { path: { season_id: season.id } }
			})
			.then(({ data }) => {
				episodeFiles = data ?? [];
			})
			.finally(() => {
				loading = false;
			});
	});

	type EpisodeRow = {
		episode: Season['episodes'][number];
		file: PublicEpisodeFile | null;
		fileIndex: number;
		rowSpan: number;
		isFirstForEpisode: boolean;
	};

	let episodeRows = $derived(
		season.episodes.flatMap((episode): EpisodeRow[] => {
			const files = (episodeFiles ?? [])
				.filter((file) => file.episode_id === episode.id)
				.sort((a, b) =>
					(a.relative_path ?? a.file_path).localeCompare(b.relative_path ?? b.file_path)
				);
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
</script>

<Dialog.Root bind:open={() => dialogState.open, (v) => (dialogState.open = v)}>
	<Dialog.Trigger
		class="group relative block aspect-2/3 w-full cursor-pointer overflow-hidden rounded-lg bg-muted/50 text-left ring-1 ring-border transition-shadow hover:shadow-lg"
	>
		<MediaImage
			media={posterMedia}
			className="h-full w-full object-cover transition-transform duration-200 group-hover:scale-105"
			loading="lazy"
		/>
		<div
			class="absolute inset-0 flex flex-col justify-end gap-0.5 bg-gradient-to-t from-black/90 via-black/40 to-transparent p-2 pb-6 text-left text-white"
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
	</Dialog.Trigger>
	<Dialog.Content class="max-h-[90vh] w-fit min-w-[90vw] overflow-y-auto sm:min-w-[600px] lg:min-w-[900px]">
		<Dialog.Header>
			<Dialog.Title>{getFullyQualifiedMediaName(show)} - {season.name}</Dialog.Title>
		</Dialog.Header>

		{#if season.overview}
			<p class="text-justify text-sm leading-6 hyphens-auto text-muted-foreground">
				{season.overview}
			</p>
		{/if}

		<Card.Root class="w-full">
			<Card.Content class="w-full overflow-x-auto">
				{#if loading}
					<div class="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
						<LoaderCircle class="size-4 animate-spin" />
						Loading episode files…
					</div>
				{:else}
					<Table.Root class="w-full table-fixed">
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
									? shallowDialog(
											`seasonFiles:${season.id}:episodeFileDetails:${row.episode.id}:${row.fileIndex}`
										)
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
				{/if}
			</Card.Content>
		</Card.Root>
	</Dialog.Content>
</Dialog.Root>
