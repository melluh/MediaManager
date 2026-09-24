<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import type { ComponentProps } from 'svelte';
	import type { PublicEpisodeFile, PublicShow } from '$lib/api/api';
	import SeasonPosterCard from '$lib/components/season-poster-card.svelte';
	import SeasonEpisodeFilesTable from '$lib/components/season-episode-files-table.svelte';
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
		posterMedia: ComponentProps<typeof SeasonPosterCard>['posterMedia'];
		banner: { label: string; classes: string };
	} = $props();

	const dialogState = $derived(shallowDialog(`seasonFiles:${season.id}`));

	let episodeFiles = $state<PublicEpisodeFile[] | null>(null);

	// Fetched each time the dialog opens, so it reflects imports since last time.
	$effect(() => {
		if (!dialogState.open) {
			untrack(() => {
				episodeFiles = null;
			});
			return;
		}
		client
			.GET('/api/v1/tv/seasons/{season_id}/files', {
				params: { path: { season_id: season.id } }
			})
			.then(({ data }) => {
				episodeFiles = data ?? [];
			})
			.catch(() => {
				episodeFiles = [];
			});
	});
</script>

<Dialog.Root bind:open={dialogState.open}>
	<Dialog.Trigger>
		{#snippet child({ props })}
			<SeasonPosterCard
				{...props}
				{posterMedia}
				name={season.name}
				episodeCount={season.episodes.length}
				{banner}
			/>
		{/snippet}
	</Dialog.Trigger>
	<Dialog.Content
		class="max-h-[90vh] w-fit min-w-[90vw] overflow-y-auto sm:min-w-[600px] lg:min-w-[900px]"
	>
		<Dialog.Header>
			<Dialog.Title>{show.name} - {season.name}</Dialog.Title>
		</Dialog.Header>

		{#if season.overview}
			<p class="text-justify text-sm leading-6 hyphens-auto text-muted-foreground">
				{season.overview}
			</p>
		{/if}

		<Card.Root class="w-full">
			<Card.Content class="w-full overflow-x-auto">
				{#if episodeFiles === null}
					<div class="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
						<LoaderCircle class="size-4 animate-spin" />
						Loading episode files…
					</div>
				{:else}
					<SeasonEpisodeFilesTable {season} {episodeFiles} />
				{/if}
			</Card.Content>
		</Card.Root>
	</Dialog.Content>
</Dialog.Root>
