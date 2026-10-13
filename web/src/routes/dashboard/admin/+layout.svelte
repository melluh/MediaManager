<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { getCurrentUser } from '$lib/context.svelte';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();

	let currentUser = getCurrentUser();

	// These pages are admin-only. The backend enforces this on every /admin/*
	// call; this redirect is just so a non-admin who reaches a URL directly
	// doesn't sit on an empty page.
	$effect(() => {
		if (!currentUser().is_superuser) {
			goto(resolve('/dashboard', {}));
		}
	});
</script>

{@render children()}
