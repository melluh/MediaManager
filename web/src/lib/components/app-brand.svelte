<script lang="ts">
	import logo from '$lib/images/logo.svg';
	import { PUBLIC_VERSION } from '$env/static/public';

	type Size = 'sm' | 'md' | 'lg';

	const sizeClasses: Record<Size, { img: string; name: string }> = {
		sm: { img: 'size-7', name: 'text-base font-bold' },
		md: { img: 'size-12', name: 'text-sm font-semibold' },
		lg: { img: 'size-12', name: 'text-2xl font-bold' }
	};

	let {
		size = 'sm',
		showVersion = false
	}: {
		size?: Size;
		showVersion?: boolean;
	} = $props();

	let classes = $derived(sizeClasses[size]);
</script>

<img alt="MediaManager Logo" class={classes.img} src={logo} />
{#if showVersion}
	<div class="grid flex-1 text-left leading-tight">
		<span class="truncate {classes.name}">MediaManager</span>
		<span class="hidden truncate text-xs text-muted-foreground sm:block">{PUBLIC_VERSION}</span>
	</div>
{:else}
	<span class={classes.name}>MediaManager</span>
{/if}
