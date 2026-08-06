<script lang="ts">
	import { getFullyQualifiedMediaName } from '$lib/utils.js';
	import { env } from '$env/dynamic/public';

	const apiUrl = env.PUBLIC_API_URL;
	let {
		media,
		className = 'h-full w-full rounded-lg object-cover',
		loading = 'lazy',
		loaded = $bindable(false)
	}: {
		media: {
			id?: string | null;
			name: string;
			year: number | null;
			metadata_updated_at?: string | null;
		};
		className?: string;
		loading?: 'lazy' | 'eager';
		loaded?: boolean;
	} = $props();

	let versionQuery = $derived(
		media.metadata_updated_at ? `?v=${new Date(media.metadata_updated_at).getTime()}` : ''
	);
</script>

<picture>
	<source srcset="{apiUrl}/api/v1/static/image/{media.id}.avif{versionQuery}" type="image/avif" />
	<source srcset="{apiUrl}/api/v1/static/image/{media.id}.webp{versionQuery}" type="image/webp" />
	<img
		alt="{getFullyQualifiedMediaName(media)}'s Poster Image"
		class={className}
		src="{apiUrl}/api/v1/static/image/{media.id}.jpeg{versionQuery}"
		{loading}
		decoding="async"
		onload={() => (loaded = true)}
		onerror={() => (loaded = true)}
	/>
</picture>
