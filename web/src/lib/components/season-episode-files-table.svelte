<script lang="ts">
	import * as Table from '$lib/components/ui/table/index.js';
	import type { PublicEpisodeFile, PublicShow } from '$lib/api/api';
	import MediaFileCells from '$lib/components/media-file-cells.svelte';
	import TruncatedText from '$lib/components/truncated-text.svelte';
	import { padSeasonOrEpisodeNumber } from '$lib/utils';

	type Season = PublicShow['seasons'][number];

	let { season, episodeFiles }: { season: Season; episodeFiles: PublicEpisodeFile[] } = $props();

	type EpisodeRow = {
		episode: Season['episodes'][number];
		file: PublicEpisodeFile | null;
		fileIndex: number;
		rowSpan: number;
		isFirstForEpisode: boolean;
	};

	// One row per file, so an episode with several versions spans several rows.
	let episodeRows = $derived(
		season.episodes.flatMap((episode): EpisodeRow[] => {
			const files = episodeFiles
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
			<Table.Row>
				{#if row.isFirstForEpisode}
					<Table.Cell rowspan={row.rowSpan} class="w-[100px] align-top font-medium">
						E{padSeasonOrEpisodeNumber(row.episode.number)}
					</Table.Cell>
					<Table.Cell rowspan={row.rowSpan} class="min-w-[50px] align-top">
						{row.episode.title}
					</Table.Cell>
				{/if}
				{#if row.file}
					<Table.Cell class="font-mono text-xs">
						<TruncatedText
							text={row.file.relative_path ?? row.file.file_path}
							tooltip={row.file.file_path}
						/>
					</Table.Cell>
					<MediaFileCells
						file={row.file}
						dialogKey={`seasonFiles:${season.id}:episodeFileDetails:${row.episode.id}:${row.fileIndex}`}
					/>
				{:else}
					<Table.Cell colspan={4} class="text-center text-sm text-muted-foreground">
						Not downloaded yet
					</Table.Cell>
				{/if}
			</Table.Row>
		{/each}
	</Table.Body>
</Table.Root>
