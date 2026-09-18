<script lang="ts">
	import { buttonVariants } from '$lib/components/ui/button';
	import Download from '@lucide/svelte/icons/download';
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import type { PublicShow } from '$lib/api/api';
	import { cn } from '$lib/utils.ts';
	import DownloadDialogWrapper from '$lib/components/download-dialogs/download-dialog-wrapper.svelte';
	import DownloadSeasonsSelectStep from '$lib/components/download-dialogs/download-seasons-select-step.svelte';
	import DownloadSeasonsReviewStep from '$lib/components/download-dialogs/download-seasons-review-step.svelte';
	import { shallowDialog } from '$lib/hooks/shallow-dialog.svelte';

	let {
		show,
		asMenuItem = false,
		menuLabel
	}: {
		show: PublicShow;
		asMenuItem?: boolean;
		menuLabel?: string;
	} = $props();

	const dialogueState = shallowDialog('downloadSeasons');
	// A second shallow-routed entry pushed on top of the dialog's own, so the
	// mobile back button returns to the selecting step before closing the
	// dialog entirely.
	const reviewStep = shallowDialog('downloadSeasons-reviewing');

	let planError: string | null = $state(null);
	let selectedSeasonIds = $state<Set<string>>(new Set());

	let selectedSeasonNumbers = $derived(
		show.seasons.filter((s) => selectedSeasonIds.has(s.id)).map((s) => s.number)
	);

	// `dialogueState.open` derives from `page.state`, which also changes when
	// `reviewStep.open` pushes/pops its own entry — track transitions
	// ourselves so switching steps doesn't reset the selection.
	let wasDialogOpen = false;
	$effect(() => {
		const open = dialogueState.open;
		if (open === wasDialogOpen) return;
		wasDialogOpen = open;
		if (!open) return;
		untrack(() => {
			planError = null;
			selectedSeasonIds = new SvelteSet(
				show.seasons.filter((s) => !s.downloaded && s.number !== 0).map((s) => s.id)
			);
		});
	});

	function proceedToReview() {
		planError = null;
		reviewStep.open = true;
	}
</script>

<DownloadDialogWrapper
	bind:open={
		() => dialogueState.open,
		(v) => {
			// Closing via backdrop/Escape/X only ever pops one history entry;
			// while on the review step that would leave the dialog open on the
			// select step, so collapse both entries in a single traversal.
			if (!v && reviewStep.open) {
				history.go(-2);
			} else {
				dialogueState.open = v;
			}
		}
	}
	triggerText="Download"
	triggerClass={cn(
		buttonVariants({ variant: 'default' }),
		'bg-blue-600 text-white hover:bg-blue-700'
	)}
	{asMenuItem}
	{menuLabel}
	title="Download Seasons"
	description="Select which seasons to download - we'll find the best torrents for you to review before anything starts."
>
	{#snippet triggerIcon()}
		<Download />
	{/snippet}

	{#if reviewStep.open}
		<DownloadSeasonsReviewStep
			{show}
			{selectedSeasonNumbers}
			onBack={() => (reviewStep.open = false)}
			onSearchError={(message) => {
				planError = message;
				reviewStep.open = false;
			}}
		/>
	{:else}
		<DownloadSeasonsSelectStep
			{show}
			bind:selectedSeasonIds
			error={planError}
			onProceed={proceedToReview}
		/>
	{/if}
</DownloadDialogWrapper>
