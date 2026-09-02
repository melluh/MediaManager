<script lang="ts">
	import LoginCard from '$lib/components/auth/login-card.svelte';
	import PageLoading from '$lib/components/page-loading.svelte';
	import PageLoadError from '$lib/components/page-load-error.svelte';
	import { getContext } from 'svelte';
	import type { AuthMetadata } from '$lib/api/api';

	const authMetadata: () => AuthMetadata | undefined = getContext('authMetadata');
	const authStatus: () => 'loading' | 'ready' | 'error' = getContext('authMetadataStatus');
</script>

<svelte:head>
	<title>Login - MediaManager</title>
	<meta
		content="Login to MediaManager - Access your personal media management dashboard"
		name="description"
	/>
</svelte:head>

<main>
	{#if authStatus() === 'error'}
		<PageLoadError
			title="Login unavailable"
			message="Could not reach the MediaManager backend to determine the available login options. Please try again in a moment."
		/>
	{:else if authStatus() === 'loading' || !authMetadata()}
		<PageLoading message="Loading login options…" />
	{:else}
		<LoginCard
			oauthProviderNames={authMetadata()!.oauth_providers}
			registrationEnabled={authMetadata()!.registration_enabled}
			passwordLoginEnabled={authMetadata()!.password_login_enabled}
		/>
	{/if}
</main>
