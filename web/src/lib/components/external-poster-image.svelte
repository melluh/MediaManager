<script lang="ts">
	import type { ExternalPosterImage } from '$lib/api/api';

	let {
		posterImages,
		alt,
		className = '',
		sizes = '(min-width: 1536px) 18vw, (min-width: 1280px) 22vw, (min-width: 1024px) 30vw, (min-width: 768px) 45vw, 90vw',
		loading = 'lazy'
	}: {
		posterImages?: ExternalPosterImage[];
		alt: string;
		className?: string;
		sizes?: string;
		loading?: 'lazy' | 'eager';
	} = $props();

	const availableImages = $derived((posterImages ?? []).filter((image) => image.url?.length > 0));
	const dimensionedImages = $derived(
		availableImages
			.filter((image) => image.width != null)
			.sort((a, b) => (a.width ?? 0) - (b.width ?? 0))
	);
	const fallbackImage = $derived(
		availableImages.find((image) => image.width == null && image.height == null) ??
			dimensionedImages.at(-1) ??
			null
	);
	const srcset = $derived(
		dimensionedImages.map((image) => `${image.url} ${image.width}w`).join(', ')
	);
</script>

{#if fallbackImage}
	<img
		class={className}
		src={fallbackImage.url}
		srcset={srcset || undefined}
		sizes={srcset ? sizes : undefined}
		{alt}
		{loading}
		decoding="async"
	/>
{/if}
