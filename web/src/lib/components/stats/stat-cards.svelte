<script lang="ts">
	import Card from '$lib/components/stats/card.svelte';
	import { onMount } from 'svelte';
	import client from '$lib/api';
	import { resolve } from '$app/paths';
	import AnimatedCard from '$lib/components/stats/animated-card.svelte';
	import type { MediaImportSuggestion } from '$lib/api/api';
	let {
		showCount,
		moviesCount,
		importableShows,
		importableMovies
	}: {
		showCount: number;
		moviesCount: number;
		importableShows: MediaImportSuggestion[];
		importableMovies: MediaImportSuggestion[];
	} = $props();

	let episodeCount: Promise<number> = $state(
		client.GET('/api/v1/tv/episodes/count').then((res) => {
			return Number(res.data ?? 0);
		})
	);
	let torrentCount: Promise<number> = $state(
		client.GET('/api/v1/torrent').then((res) => {
			return res.data?.length ?? 0;
		})
	);

	let installedVersion: string | undefined = $state(undefined);
	let newestVersion: string | null = $state(null);
	let updateAvailable: boolean = $state(false);

	onMount(async () => {
		let health = await client.GET('/api/v1/version');
		if (health.data) {
			installedVersion = health.data.version;
			newestVersion = health.data.latest_version ?? null;
			updateAvailable = health.data.update_available ?? false;
		}
	});
</script>

<div class="flex flex-wrap gap-2">
	<div class="flex-auto">
		<AnimatedCard title="TV Shows" footer="Total count of TV shows" number={showCount}
		></AnimatedCard>
	</div>
	<div class="flex-auto">
		{#await episodeCount then episodes}
			<AnimatedCard title="Episodes" footer="Total count of downloaded episodes" number={episodes}
			></AnimatedCard>
		{/await}
	</div>
	<div class="flex-auto">
		<AnimatedCard title="Movies" footer="Total count of movies" number={moviesCount}></AnimatedCard>
	</div>
	<div class="flex-auto">
		{#await torrentCount then torrent}
			<AnimatedCard title="Torrents" footer="Total count of torrents/NZBs" number={torrent}
			></AnimatedCard>
		{/await}
	</div>
	{#if importableShows.length > 0}
		<div class="flex-auto">
			<Card title="Detected TV shows!" footer="Count of detected TV shows ready to import">
				<a rel="external" target="_blank" href={resolve('/dashboard/tv/', {})} class="underline">
					{importableShows.length}
				</a>
			</Card>
		</div>
	{/if}
	{#if importableMovies.length > 0}
		<div class="flex-auto">
			<Card title="Detected movies!" footer="Count of detected movies ready to import">
				<a
					rel="external"
					target="_blank"
					href={resolve('/dashboard/movies/', {})}
					class="underline"
				>
					{importableMovies.length}
				</a>
			</Card>
		</div>
	{/if}
	<div class="flex-auto">
		{#if updateAvailable}
			<Card title="New version available!" footer="A new version of MediaManager is available!">
				<a
					rel="external"
					target="_blank"
					href="https://github.com/maxdorninger/MediaManager/releases"
					class="underline"
				>
					{installedVersion} → v{newestVersion}
				</a>
			</Card>
		{/if}
	</div>
</div>
