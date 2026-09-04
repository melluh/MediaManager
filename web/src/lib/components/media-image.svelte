<script lang="ts">
	import { getFullyQualifiedMediaName } from '$lib/utils.js';
	import { env } from '$env/dynamic/public';

	const apiUrl = env.PUBLIC_API_URL;
	let {
		media,
		variant = 'poster',
		className,
		loading,
		loaded = $bindable(false)
	}: {
		media: {
			id?: string | null;
			name: string;
			year: number | null;
			metadata_updated_at?: string | null;
			images?: Record<string, string> | null;
		};
		variant?: 'poster' | 'backdrop';
		className?: string;
		loading?: 'lazy' | 'eager';
		loaded?: boolean;
	} = $props();

	// The backend only reports an image here once it's actually been
	// downloaded to disk, so its presence/absence is authoritative - no more
	// guessing a URL and reacting to onerror.
	let imagePath = $derived(media.images?.[variant]);
	let resolvedClassName = $derived(
		className ??
			(variant === 'backdrop'
				? 'h-full w-full object-cover'
				: 'h-full w-full rounded-lg object-cover')
	);
	let resolvedLoading = $derived(loading ?? (variant === 'backdrop' ? 'eager' : 'lazy'));
	let versionQuery = $derived(
		media.metadata_updated_at ? `?v=${new Date(media.metadata_updated_at).getTime()}` : ''
	);

	// `imagePath` (and so which image, if any, is mounted below) can change
	// under the same component instance - e.g. a caller reusing this
	// component across a media change. Reset `loaded` so a caller's skeleton
	// waits for the new image's `onload`, or - if there's nothing to mount -
	// don't wait for an `onload` that will never fire.
	$effect(() => {
		loaded = imagePath === undefined;
	});
</script>

{#if imagePath}
	<picture>
		<source srcset="{apiUrl}{imagePath}.avif{versionQuery}" type="image/avif" />
		<source srcset="{apiUrl}{imagePath}.webp{versionQuery}" type="image/webp" />
		<img
			alt="{getFullyQualifiedMediaName(media)}'s {variant === 'backdrop'
				? 'Backdrop'
				: 'Poster'} Image"
			class={resolvedClassName}
			src="{apiUrl}{imagePath}.jpg{versionQuery}"
			loading={resolvedLoading}
			decoding="async"
			onload={() => (loaded = true)}
		/>
	</picture>
{/if}
