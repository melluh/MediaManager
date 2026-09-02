<script lang="ts">
	import SignupCard from '$lib/components/auth/signup-card.svelte';
	import PageLoading from '$lib/components/page-loading.svelte';
	import PageLoadError from '$lib/components/page-load-error.svelte';
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import type { AuthMetadata } from '$lib/api/api';

	const authMetadata: () => AuthMetadata | undefined = getContext('authMetadata');
	const authStatus: () => 'loading' | 'ready' | 'error' = getContext('authMetadataStatus');

	// The metadata arrives after this page has already painted, so the
	// "registration is disabled" bounce happens here rather than in a `load`.
	$effect(() => {
		if (authStatus() === 'ready' && !authMetadata()?.registration_enabled) {
			goto(resolve('/login', {}), { replaceState: true });
		}
	});
</script>

<svelte:head>
	<title>Login - MediaManager</title>
	<meta content="Signup - MediaManager" name="description" />
</svelte:head>

{#if authStatus() === 'error'}
	<PageLoadError
		title="Signup unavailable"
		message="Could not reach the MediaManager backend. Please try again in a moment."
	/>
{:else if authStatus() === 'loading' || !authMetadata()}
	<PageLoading message="Loading signup options…" />
{:else}
	<SignupCard oauthProviderNames={authMetadata()!.oauth_providers} />
{/if}
