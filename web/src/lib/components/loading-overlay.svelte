<script lang="ts">
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';

	// Covers its nearest positioned ancestor, typically placeholder skeletons.
	let { message }: { message: string } = $props();
</script>

<div
	class="absolute inset-0 flex flex-col items-center justify-center gap-2 rounded-lg bg-background/70 backdrop-blur-sm"
>
	<LoaderCircle class="size-6 animate-spin text-muted-foreground" />
	<span class="text-sm text-muted-foreground">{message}</span>
</div>
