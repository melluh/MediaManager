<script lang="ts">
	import Skeleton from '$lib/components/ui/skeleton/skeleton.svelte';

	let {
		detailsLoaded,
		tagline,
		overview
	}: {
		detailsLoaded: boolean;
		tagline: string | null | undefined;
		overview: string | null | undefined;
	} = $props();
</script>

<div class="flex h-full flex-col gap-3 overflow-y-auto px-6 pb-6">
	{#if detailsLoaded}
		{#if tagline}
			<p class="text-lg font-medium text-muted-foreground italic">{tagline}</p>
		{/if}
	{:else}
		<Skeleton class="h-6 w-64" />
	{/if}

	<p class="text-base text-muted-foreground">
		{overview !== '' && overview != null ? overview : 'No overview available'}
	</p>
</div>
