<script lang="ts">
	import * as Card from '$lib/components/ui/card/index.js';
	import { getContext } from 'svelte';
	import UserSettings from '$lib/components/user-settings.svelte';
	import type { Crumb } from '$lib/components/nav/dashboard-header.svelte';
	import PageLoading from '$lib/components/page-loading.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const setCrumbs: (crumbs: Crumb[]) => void = getContext('setCrumbs');
	setCrumbs([{ label: 'My Account' }]);

	// `data.passwordLoginEnabled` is re-created as a new promise on every
	// invalidateAll(). Awaiting it directly in the markup would remount
	// UserSettings on every save, wiping its local state. Instead resolve
	// into local state once and update in place.
	let passwordLoginEnabled: boolean | undefined = $state();

	$effect(() => {
		const promise = data.passwordLoginEnabled;
		promise.then((p) => {
			if (promise === data.passwordLoginEnabled) passwordLoginEnabled = p;
		});
	});
</script>

<svelte:head>
	<title>My Account - MediaManager</title>
	<meta content="Manage your MediaManager account settings" name="description" />
</svelte:head>

<main class="mx-auto flex w-full flex-1 flex-col gap-4 p-4 md:max-w-[80em]">
	<h1 class="my-6 scroll-m-20 text-center text-4xl font-extrabold tracking-tight lg:text-5xl">
		My Account
	</h1>
	<Card.Root id="me">
		<Card.Header>
			<Card.Title>Your account</Card.Title>
		</Card.Header>
		<Card.Content>
			{#if passwordLoginEnabled === undefined}
				<PageLoading message="Loading account settings…" />
			{:else}
				<UserSettings {passwordLoginEnabled} />
			{/if}
		</Card.Content>
	</Card.Root>
</main>
