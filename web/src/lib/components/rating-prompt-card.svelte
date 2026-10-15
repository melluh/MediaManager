<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import MediaImage from '$lib/components/media-image.svelte';
	import RatingScale from '$lib/components/rating-scale.svelte';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import Check from '@lucide/svelte/icons/check';
	import { onDestroy } from 'svelte';
	import { fade, slide, type SlideParams } from 'svelte/transition';
	import { toast } from 'svelte-sonner';
	import type { RatingPrompt } from '$lib/api/api';
	import client from '$lib/api';
	import { saveRating } from '$lib/rating';
	import { formatAddedTime } from '$lib/utils';
	import { resolve } from '$app/paths';

	let { prompts }: { prompts: RatingPrompt[] } = $props();

	const CONFIRMATION_MS = 2000;

	// Answered prompts are dropped locally, so the next one shows without
	// refetching.
	let answeredIds: string[] = $state([]);
	let current = $derived(prompts.find((p) => !answeredIds.includes(p.media.id)));
	// After an answer is saved, the card confirms it for a moment before it
	// animates out (`leaving`), so it doesn't vanish from under the click.
	let status: 'idle' | 'saving' | 'saved' = $state('idle');
	let leaving = $state(false);
	// The answer being saved/confirmed; null for "Skip".
	let answeredScore: number | null = $state(null);
	let confirmationTimeout: ReturnType<typeof setTimeout> | undefined;
	onDestroy(() => clearTimeout(confirmationTimeout));
	let posterLoaded = $state(false);
	let watchedLabel = $derived(current ? `Watched ${formatAddedTime(current.watched_at)}` : '');
	let movieHref = $derived(
		current
			? resolve('/dashboard/movies/[movieId]', {
					movieId: current.media.slug ?? current.media.id
				})
			: undefined
	);

	async function answer(score: number | null) {
		if (!current || status !== 'idle') return;
		const movieId = current.media.id;
		status = 'saving';
		answeredScore = score;
		try {
			if (score === null) {
				const { response } = await client.POST('/api/v1/ratings/movies/{movie_id}/dismiss', {
					params: { path: { movie_id: movieId } }
				});
				if (!response.ok) throw new Error(`Dismissing failed: ${response.status}`);
			} else {
				await saveRating(movieId, false, score);
			}
			status = 'saved';
			confirmationTimeout = setTimeout(() => (leaving = true), CONFIRMATION_MS);
		} catch {
			toast.error('Failed to save your answer');
			status = 'idle';
			answeredScore = null;
		}
	}

	// Runs once the answered prompt has animated out, bringing in the next one.
	function showNext() {
		if (!current) return;
		answeredIds = [...answeredIds, current.media.id];
		status = 'idle';
		answeredScore = null;
		posterLoaded = false;
		leaving = false;
	}

	// Collapses the card's height (and margins) while fading it.
	function slideFade(node: Element, params?: SlideParams) {
		const transition = slide(node, params);
		return {
			...transition,
			css: (t: number, u: number) => `${transition.css?.(t, u) ?? ''} opacity: ${t};`
		};
	}
</script>

{#if current && movieHref && !leaving}
	<div
		class="mx-auto mt-4 mb-8 lg:pointer-fine:px-12"
		transition:slideFade={{ duration: 300 }}
		onoutroend={showNext}
	>
		<!-- Sized to its content from md up, so the scale sits right under the
		     question rather than across the page from it. -->
		<div class="flex items-center gap-4 rounded-xl border bg-card p-4 shadow-sm md:w-fit">
			<!-- eslint-disable svelte/no-navigation-without-resolve -- href is built from resolve() in movieHref -->
			<a
				href={movieHref}
				class="relative hidden aspect-2/3 w-20 shrink-0 overflow-hidden rounded-md bg-muted md:block"
				title={current.media.name}
			>
				<MediaImage
					media={current.media}
					className="h-full w-full object-cover"
					bind:loaded={posterLoaded}
				/>
				{#if !posterLoaded}
					<Skeleton class="absolute inset-0 h-full w-full" />
				{/if}
			</a>
			<!-- From md up the scale and the row under it get a fixed width, about
			     that of the scale on the detail pages; full width on mobile. -->
			<div class="flex min-w-0 flex-1 flex-col gap-2">
				<h3 class="text-lg font-semibold">
					Did you enjoy
					<a href={movieHref} class="hover:underline">{current.media.name}</a>?
				</h3>
				<!-- eslint-enable svelte/no-navigation-without-resolve -->
				<RatingScale
					class="flex w-full md:w-64"
					value={answeredScore}
					pending={status === 'saving'}
					onSelect={answer}
				/>
				<!-- Fixed height, so nothing shifts as the status changes. -->
				<div class="flex h-8 items-center justify-between gap-2 md:w-64">
					<p class="truncate text-xs text-muted-foreground">{watchedLabel}</p>
					{#if status === 'idle'}
						<Button variant="ghost" size="sm" onclick={() => answer(null)}>Skip</Button>
					{:else if status === 'saving'}
						<LoaderCircle class="mr-3 size-4 animate-spin text-muted-foreground" />
					{:else}
						<span
							class="mr-3 inline-flex items-center gap-1.5 text-sm text-muted-foreground"
							in:fade={{ duration: 150 }}
						>
							<Check class="size-4 text-brand" />
							{answeredScore === null ? 'Skipped' : 'Thanks!'}
						</span>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/if}
