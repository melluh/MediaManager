<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Tabs from '$lib/components/ui/tabs';
	import Download from '@lucide/svelte/icons/download';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import HardDrive from '@lucide/svelte/icons/hard-drive';
	import { toast } from 'svelte-sonner';
	import { invalidateAll } from '$app/navigation';
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import client from '$lib/api';
	import type { PublicShow, SeasonDownloadPlan } from '$lib/api/api';
	import LoadingOverlay from '$lib/components/loading-overlay.svelte';
	import SeasonPlanTable from '$lib/components/download-dialogs/season-plan-table.svelte';
	import SeasonPlanGaps from '$lib/components/download-dialogs/season-plan-gaps.svelte';
	import { formatSize } from '$lib/components/download-dialogs/torrent-format';
	import { totalSize, type PickStatus } from '$lib/components/download-dialogs/season-plan';

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

	let acceptedCount = $derived(acceptedPickIdsBySlot[activeSlotName]?.size ?? 0);
	let acceptedTotalSize = $derived.by(() => {
		if (!activeSlot) return 0;
		const accepted = acceptedPickIdsBySlot[activeSlotName] ?? new Set<string>();
		return totalSize(activeSlot.picks.filter((p) => accepted.has(p.result.id as string)));
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
						? 'A file or pending download for this version already exists. Pick a different release.'
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
			<LoadingOverlay message="Searching for torrents..." />
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
								{formatSize(totalSize(slot.picks))}
							</span>
						</Tabs.Trigger>
					{/each}
				</Tabs.List>
				{#each plan.slots as slot (slot.slot_name)}
					<Tabs.Content value={slot.slot_name} class="flex flex-col gap-2">
						<SeasonPlanTable
							planSlot={slot}
							accepted={acceptedPickIdsBySlot[slot.slot_name] ?? new Set()}
							{pickStatus}
							{pickErrorMessage}
							disabled={isDownloading}
							onToggle={togglePick}
						/>
						{#if slot.gaps.length > 0}
							<SeasonPlanGaps gaps={slot.gaps} />
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
				acceptedCount === 0}
			onclick={confirmDownloads}
		>
			{#if isDownloading}
				<LoaderCircle class="animate-spin" />
			{:else}
				<Download />
			{/if}
			{#if !isSearching && acceptedTotalSize > 0 && acceptedCount > 0}
				Download ({formatSize(acceptedTotalSize)})
			{:else}
				Download
			{/if}
		</Button>
	</div>
</div>
