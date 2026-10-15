<script lang="ts">
	import ThumbsUp from '@lucide/svelte/icons/thumbs-up';
	import ThumbsDown from '@lucide/svelte/icons/thumbs-down';
	import Heart from '@lucide/svelte/icons/heart';
	import HeartCrack from '@lucide/svelte/icons/heart-crack';
	import { cn } from '$lib/utils';

	// Thumbs for a like/dislike; a heart and a broken heart for the stronger
	// love/hate ratings.
	let { score, filled = false }: { score: number; filled?: boolean } = $props();

	let Icon = $derived.by(() => {
		if (score >= 2) return Heart;
		if (score <= -2) return HeartCrack;
		return score > 0 ? ThumbsUp : ThumbsDown;
	});
</script>

<Icon class={cn(filled && 'fill-current')} />
