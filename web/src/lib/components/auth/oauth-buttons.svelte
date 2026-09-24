<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import LogInIcon from '@lucide/svelte/icons/log-in';
	import Spinner from '$lib/components/ui/spinner/spinner.svelte';

	let {
		providerNames,
		divider = true,
		primary = false,
		loading,
		onclick
	}: {
		providerNames: string[];
		/** Show an "Or continue with" divider above the buttons, below another login form. */
		divider?: boolean;
		/** Style the buttons as the main action, when OAuth is the only way to log in. */
		primary?: boolean;
		loading: boolean;
		onclick: () => void;
	} = $props();
</script>

{#if divider && providerNames.length > 0}
	<div
		class="relative mt-4 text-center text-sm after:absolute after:inset-0 after:top-1/2 after:z-0 after:flex after:items-center after:border-t after:border-border"
	>
		<span class="relative z-10 bg-background px-2 text-muted-foreground">Or continue with</span>
	</div>
{/if}

{#each providerNames as name, i (name)}
	<Button
		class={divider || i > 0 ? 'mt-2 w-full' : 'w-full'}
		disabled={loading}
		{onclick}
		variant={primary ? 'default' : 'outline'}
	>
		{#if loading}
			<Spinner />
		{:else if primary}
			<LogInIcon class="size-4" />
		{/if}
		Login with {name}
	</Button>
{/each}
