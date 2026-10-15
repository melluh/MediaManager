<script lang="ts">
	import type { Snippet } from 'svelte';
	import { cn } from '$lib/utils';

	let { class: className, children }: { class?: string; children: Snippet } = $props();
</script>

<!-- Smaller and left-aligned on phones and tablets, centered on desktop
     (the same lg + fine pointer breakpoint as the rest of the layout).
     Hidden on landscape tablets, where the header's breadcrumbs already
     name the page. -->
<h1
	class={cn(
		'scroll-m-20 text-3xl font-extrabold tracking-tight lg:pointer-coarse:hidden lg:pointer-fine:text-center lg:pointer-fine:text-5xl',
		className
	)}
>
	{@render children()}
</h1>
