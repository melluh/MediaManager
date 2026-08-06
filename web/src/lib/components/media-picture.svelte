<script>
	import { getFullyQualifiedMediaName } from '$lib/utils.js';
	import { env } from '$env/dynamic/public';

	const apiUrl = env.PUBLIC_API_URL;
	let { media, loaded = $bindable(false) } = $props();

	let versionQuery = $derived(
		media.metadata_updated_at ? `?v=${new Date(media.metadata_updated_at).getTime()}` : ''
	);
</script>

<picture>
	<source srcset="{apiUrl}/api/v1/static/image/{media.id}.avif{versionQuery}" type="image/avif" />
	<source srcset="{apiUrl}/api/v1/static/image/{media.id}.webp{versionQuery}" type="image/webp" />
	<img
		alt="{getFullyQualifiedMediaName(media)}'s Poster Image"
		class="h-full w-full rounded-lg object-cover"
		src="{apiUrl}/api/v1/static/image/{media.id}.jpeg{versionQuery}"
		decoding="async"
		onload={() => (loaded = true)}
		onerror={() => (loaded = true)}
	/>
</picture>
