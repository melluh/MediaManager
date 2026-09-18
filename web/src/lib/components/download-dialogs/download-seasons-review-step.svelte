<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Tabs from '$lib/components/ui/tabs';
	import * as Table from '$lib/components/ui/table';
	import Download from '@lucide/svelte/icons/download';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import Check from '@lucide/svelte/icons/check';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import Captions from '@lucide/svelte/icons/captions';
	import Film from '@lucide/svelte/icons/film';
	import Gauge from '@lucide/svelte/icons/gauge';
	import HardDrive from '@lucide/svelte/icons/hard-drive';
	import Tag from '@lucide/svelte/icons/tag';
	import Users from '@lucide/svelte/icons/users';
	import { toast } from 'svelte-sonner';
	import { invalidateAll } from '$app/navigation';
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import client from '$lib/api';
	import type { PublicShow, SeasonDownloadPlan } from '$lib/api/api';
	import TorrentScoreValue from '$lib/components/download-dialogs/torrent-score-value.svelte';
	import TorrentIndexerLink from '$lib/components/download-dialogs/torrent-indexer-link.svelte';
	import {
		formatCodec,
		formatGroup,
		formatMbps,
		formatSeeders,
		formatSize,
		formatSubtitles
	} from '$lib/components/download-dialogs/torrent-format';

	type Slot = SeasonDownloadPlan['slots'][number];
	type Pick = Slot['picks'][number];
	type PickStatus = 'starting' | 'started' | 'failed';

	let {
		show,
		selectedSeasonNumbers,
		onBack,
		onSearchError
	}: {
		show: PublicShow;
		selectedSeasonNumbers: number[];
		onBack: () => void;
		onSearchError: (message: string) => void;
	} = $props();

	let isSearching = $state(true);
	let isDownloading = $state(false);
	let plan: SeasonDownloadPlan | null = $state(null);
	let activeSlotName = $state('');
	let acceptedPickIdsBySlot: Record<string, Set<string>> = $state({});
	let pickStatus: Record<string, PickStatus> = $state({});
	let pickErrorMessage: Record<string, string> = $state({});

	let activeSlot = $derived.by(() => {
		if (!plan) return null;
		return plan.slots.find((s) => s.slot_name === activeSlotName) ?? null;
	});

	let acceptedTotalSize = $derived.by(() => {
		if (!activeSlot) return 0;
		const accepted = acceptedPickIdsBySlot[activeSlotName] ?? new Set<string>();
		return activeSlot.picks
			.filter((p) => accepted.has(p.result.id as string))
			.reduce((total, p) => total + p.result.size, 0);
	});

	$effect(() => {
		const controller = new AbortController();
		untrack(() => search(controller));
		return () => controller.abort();
	});

	function togglePick(resultId: string) {
		const current = new SvelteSet(acceptedPickIdsBySlot[activeSlotName] ?? []);
		if (current.has(resultId)) {
			current.delete(resultId);
		} else {
			current.add(resultId);
		}
		acceptedPickIdsBySlot = { ...acceptedPickIdsBySlot, [activeSlotName]: current };
	}

	function pickSortKey(pick: Pick): [number, number] {
		if (pick.covers_episodes) {
			let best: [number, number] | null = null;
			for (const [seasonNumber, episodeNumbers] of Object.entries(pick.covers_episodes)) {
				for (const episodeNumber of episodeNumbers) {
					if (
						!best ||
						Number(seasonNumber) < best[0] ||
						(Number(seasonNumber) === best[0] && episodeNumber < best[1])
					) {
						best = [Number(seasonNumber), episodeNumber];
					}
				}
			}
			if (best) return best;
		}
		return [Math.min(...pick.covers_seasons), 0];
	}

	function sortPicks(picks: Pick[]): Pick[] {
		return picks.slice().sort((a, b) => {
			const [aSeason, aEpisode] = pickSortKey(a);
			const [bSeason, bEpisode] = pickSortKey(b);
			return aSeason - bSeason || aEpisode - bEpisode;
		});
	}

	function slotTotalSize(slot: Slot): number {
		return slot.picks.reduce((total, p) => total + p.result.size, 0);
	}

	function pickLabel(pick: Pick): string {
		if (pick.covers_episodes) {
			return Object.entries(pick.covers_episodes)
				.map(
					([seasonNumber, episodeNumbers]) =>
						`S${seasonNumber.padStart(2, '0')}` +
						episodeNumbers.map((e) => `E${String(e).padStart(2, '0')}`).join(',')
				)
				.join(', ');
		}
		const seasons = pick.covers_seasons.slice().sort((a, b) => a - b);
		const first = `S${String(seasons[0]).padStart(2, '0')}`;
		if (seasons.length === 1) return first;
		return `${first}–S${String(seasons[seasons.length - 1]).padStart(2, '0')}`;
	}

	async function search(controller: AbortController) {
		try {
			const { data, error, response } = await client.GET(
				'/api/v1/tv/shows/{show_id}/season-download-plan',
				{
					params: {
						path: { show_id: show.id },
						query: { season_numbers: selectedSeasonNumbers }
					},
					signal: controller.signal
				}
			);

			if (controller.signal.aborted) return;
			isSearching = false;

			if (!response.ok || !data) {
				const message =
					(error as { detail?: string } | undefined)?.detail ?? 'Failed to build a download plan.';
				toast.error(message);
				onSearchError(message);
				return;
			}

			plan = data;
			activeSlotName = data.slots[0]?.slot_name ?? '';
			acceptedPickIdsBySlot = Object.fromEntries(
				data.slots.map((slot) => [
					slot.slot_name,
					new SvelteSet(
						slot.picks.filter((p) => !p.already_downloaded).map((p) => p.result.id as string)
					)
				])
			);
		} catch {
			if (controller.signal.aborted) return;
			isSearching = false;
			const message = 'Failed to build a download plan.';
			toast.error(message);
			onSearchError(message);
		}
	}

	async function confirmDownloads() {
		if (!activeSlot) return;
		const accepted = acceptedPickIdsBySlot[activeSlotName] ?? new Set<string>();
		const acceptedPicks = activeSlot.picks.filter((p) => accepted.has(p.result.id as string));
		if (acceptedPicks.length === 0) {
			toast.error('No downloads selected.');
			return;
		}

		isDownloading = true;
		let started = 0;
		let failed = 0;

		for (const pick of acceptedPicks) {
			const id = pick.result.id as string;
			pickStatus[id] = 'starting';

			const { error, response } = await client.POST('/api/v1/tv/torrents', {
				params: {
					query: {
						show_id: show.id,
						public_indexer_result_id: id
					}
				}
			});

			if (response.ok) {
				started++;
				pickStatus[id] = 'started';
			} else {
				failed++;
				pickStatus[id] = 'failed';
				pickErrorMessage[id] =
					response.status === 409
						? 'A file for this quality/version already exists. Pick a different release.'
						: ((error as { detail?: string } | undefined)?.detail ?? 'Failed to start download.');
			}
		}

		isDownloading = false;
		await invalidateAll();

		if (failed === 0) {
			toast.success(`${started} download${started === 1 ? '' : 's'} started successfully!`);
		} else {
			toast.error(`${started} started, ${failed} failed.`);
		}
	}
</script>

<div class="flex flex-col gap-4">
	{#if isSearching}
		<div class="relative flex flex-col gap-4">
			<div class="flex flex-wrap gap-2">
				{#each { length: 3 }}
					<Skeleton class="h-14 w-32 rounded-md" />
				{/each}
			</div>
			<div class="flex flex-col gap-2 rounded-md border p-3">
				{#each { length: 6 }}
					<Skeleton class="h-10 w-full" />
				{/each}
			</div>
			<div
				class="absolute inset-0 flex flex-col items-center justify-center gap-2 rounded-lg bg-background/70 backdrop-blur-sm"
			>
				<LoaderCircle class="size-6 animate-spin text-muted-foreground" />
				<span class="text-sm text-muted-foreground">Searching for torrents...</span>
			</div>
		</div>
	{:else if plan}
		{#if (plan.search_errors ?? []).length > 0}
			<div class="rounded-md border border-red-500/50 bg-red-500/10 p-3 text-sm">
				{#each plan.search_errors ?? [] as searchError (searchError)}
					<p>{searchError}</p>
				{/each}
			</div>
		{/if}

		{#if plan.slots.length === 0}
			<p class="text-sm text-muted-foreground">
				No torrents matched any quality tier for the selected seasons.
			</p>
		{:else}
			<Tabs.Root bind:value={activeSlotName}>
				<Tabs.List class="h-auto flex-wrap justify-start gap-2 p-1.5">
					{#each plan.slots as slot (slot.slot_name)}
						<Tabs.Trigger value={slot.slot_name} class="h-auto flex-col gap-1 px-4 py-2.5">
							<span class="text-sm font-semibold">{slot.slot_label}</span>
							<span class="flex items-center gap-1 text-xs text-muted-foreground">
								<HardDrive class="size-3.5" />
								{formatSize(slotTotalSize(slot))}
							</span>
						</Tabs.Trigger>
					{/each}
				</Tabs.List>
				{#each plan.slots as slot (slot.slot_name)}
					<Tabs.Content value={slot.slot_name}>
						<div class="max-h-[42vh] overflow-y-auto rounded-md border">
							<Table.Root>
								<Table.Header class="sticky top-0 z-10 bg-background">
									<Table.Row>
										<Table.Head class="w-10"></Table.Head>
										<Table.Head>Torrent</Table.Head>
										<Table.Head>
											<div class="flex items-center gap-1">
												<HardDrive class="size-3.5" />
												Size
											</div>
										</Table.Head>
										<Table.Head>
											<div class="flex items-center gap-1">
												<Users class="size-3.5" />
												Seeders
											</div>
										</Table.Head>
										<Table.Head>
											<div class="flex items-center gap-1">
												<Gauge class="size-3.5" />
												Bitrate
											</div>
										</Table.Head>
										<Table.Head>
											<div class="flex items-center gap-1">
												<Film class="size-3.5" />
												Codec
											</div>
										</Table.Head>
										<Table.Head>
											<div class="flex items-center gap-1">
												<Captions class="size-3.5" />
												Subtitles
											</div>
										</Table.Head>
										<Table.Head>
											<div class="flex items-center gap-1">
												<Tag class="size-3.5" />
												Group
											</div>
										</Table.Head>
										<Table.Head>Score</Table.Head>
										<Table.Head class="w-8"></Table.Head>
									</Table.Row>
								</Table.Header>
								<Table.Body>
									{#each sortPicks(slot.picks) as pick (pick.result.id)}
										{@const id = pick.result.id as string}
										{@const status = pickStatus[id]}
										{@const accepted = acceptedPickIdsBySlot[slot.slot_name] ?? new Set<string>()}
										{@const subtitleSummary = formatSubtitles(pick.result.attributes?.subtitles)}
										{@const mbpsText = formatMbps(pick.result.effective_mbps)}
										{@const sizeText = formatSize(pick.result.size)}
										{@const seedersText = formatSeeders(pick.result.usenet, pick.result.seeders)}
										{@const groupText = formatGroup(pick.result.attributes?.release_group)}
										{@const codecText = formatCodec(pick.result.attributes?.codec)}
										<Table.Row>
											<Table.Cell>
												<Checkbox
													checked={accepted.has(id)}
													disabled={isDownloading || !!status}
													onCheckedChange={() => togglePick(id)}
												/>
											</Table.Cell>
											<Table.Cell class="max-w-64">
												<div class="flex flex-col gap-0.5">
													<div class="flex flex-wrap items-center gap-1.5">
														<span class="font-medium">{pickLabel(pick)}</span>
														<span class="text-muted-foreground">&middot;</span>
														<TorrentIndexerLink
															indexer={pick.result.indexer}
															comments={pick.result.comments}
														/>
														{#if pick.already_downloaded}
															<Badge variant="outline" class="text-xs">Already downloaded</Badge>
														{/if}
													</div>
													<div class="flex min-w-0 items-center gap-1">
														<span
															class="min-w-0 truncate text-xs text-muted-foreground"
															title={pick.result.title}
														>
															{pick.result.title}
														</span>
														{#if pick.result.flags.includes('freeleech')}
															<Badge
																variant="outline"
																class="shrink-0 px-1 py-0 text-[10px] text-green-500"
															>
																Freeleech
															</Badge>
														{/if}
													</div>
													{#if status === 'failed'}
														<span class="text-xs text-red-500">{pickErrorMessage[id]}</span>
													{/if}
												</div>
											</Table.Cell>
											<Table.Cell class="whitespace-nowrap">{sizeText}</Table.Cell>
											<Table.Cell class="whitespace-nowrap">{seedersText}</Table.Cell>
											<Table.Cell class="whitespace-nowrap">{mbpsText}</Table.Cell>
											<Table.Cell class="whitespace-nowrap">{codecText}</Table.Cell>
											<Table.Cell class="whitespace-nowrap">{subtitleSummary}</Table.Cell>
											<Table.Cell class="whitespace-nowrap">{groupText}</Table.Cell>
											<Table.Cell class="whitespace-nowrap">
												<TorrentScoreValue
													score={pick.result.score}
													breakdown={pick.result.score_breakdown}
												/>
											</Table.Cell>
											<Table.Cell>
												{#if status === 'starting'}
													<LoaderCircle class="size-4 animate-spin" />
												{:else if status === 'started'}
													<Check class="size-4 stroke-green-500" />
												{:else if status === 'failed'}
													<CircleX class="size-4 stroke-rose-600" />
												{/if}
											</Table.Cell>
										</Table.Row>
									{/each}
								</Table.Body>
							</Table.Root>
						</div>
						{#if slot.gaps.length > 0}
							<div class="mt-2 rounded-md border border-amber-500/50 bg-amber-500/10 p-3 text-sm">
								<p class="font-medium">No suitable torrent found for:</p>
								<ul class="list-inside list-disc">
									{#each slot.gaps as gap (gap.season_number)}
										<li>
											S{String(gap.season_number).padStart(2, '0')}
											{gap.episode_numbers.map((e) => `E${String(e).padStart(2, '0')}`).join(', ')}
											- {gap.reason}
										</li>
									{/each}
								</ul>
							</div>
						{/if}
					</Tabs.Content>
				{/each}
			</Tabs.Root>
		{/if}
	{/if}

	<div class="flex items-center justify-between gap-3">
		<Button variant="ghost" size="sm" class="w-fit" disabled={isDownloading} onclick={onBack}>
			<ArrowLeft />
			Back
		</Button>
		<Button
			class="w-fit"
			disabled={isSearching ||
				!plan ||
				plan.slots.length === 0 ||
				isDownloading ||
				(acceptedPickIdsBySlot[activeSlotName]?.size ?? 0) === 0}
			onclick={confirmDownloads}
		>
			{#if isDownloading}
				<LoaderCircle class="animate-spin" />
			{:else}
				<Download />
			{/if}
			{#if !isSearching && acceptedTotalSize > 0 && (acceptedPickIdsBySlot[activeSlotName]?.size ?? 0) > 0}
				Download ({formatSize(acceptedTotalSize)})
			{:else}
				Download
			{/if}
		</Button>
	</div>
</div>
