<script lang="ts">
	import RatingScale from '$lib/components/rating-scale.svelte';
	import { toast } from 'svelte-sonner';
	import { fetchRating, saveRating } from '$lib/rating';

	let { mediaId, isShow }: { mediaId: string; isShow: boolean } = $props();

	// Fetched separately from the media's own details so it never holds up the
	// detail page.
	let score: number | null = $state(null);
	let saving = $state(false);
	$effect(() => {
		const id = mediaId;
		score = null;
		fetchRating(id, isShow)
			.then((fetched) => {
				if (id === mediaId) score = fetched;
			})
			.catch(() => {
				// leave unrated; the user can still rate
			});
	});

	async function rate(target: number) {
		if (saving) return;
		const previous = score;
		// Clicking the active rating again clears it.
		const next = score === target ? null : target;
		score = next;
		saving = true;
		try {
			await saveRating(mediaId, isShow, next);
		} catch {
			score = previous;
			toast.error('Failed to save your rating');
		} finally {
			saving = false;
		}
	}
</script>

<RatingScale class="flex w-full" value={score} pending={saving} onSelect={rate} />
