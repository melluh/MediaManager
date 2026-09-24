<script lang="ts">
	import * as Card from '$lib/components/ui/card/index.js';
	import { setCrumbs } from '$lib/context.svelte';
	import { Resolved } from '$lib/hooks/resolved.svelte';
	import PageHeading from '$lib/components/page-heading.svelte';
	import UserSettings from '$lib/components/user-settings.svelte';
	import PageLoading from '$lib/components/page-loading.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	setCrumbs([{ label: 'My Account' }]);

	// Resolved in place rather than awaited in markup, so saving (which calls
	// invalidateAll()) doesn't remount UserSettings and wipe its local state.
	const passwordLoginEnabled = new Resolved(() => data.passwordLoginEnabled);
</script>

<svelte:head>
	<title>My Account - MediaManager</title>
	<meta content="Manage your MediaManager account settings" name="description" />
</svelte:head>

<main class="mx-auto flex w-full flex-1 flex-col gap-4 p-4 md:max-w-[80em]">
	<PageHeading class="my-6">My Account</PageHeading>
	<Card.Root id="me">
		<Card.Header>
			<Card.Title>Your account</Card.Title>
		</Card.Header>
		<Card.Content>
			{#if passwordLoginEnabled.value === undefined}
				<PageLoading message="Loading account settings…" />
			{:else}
				<UserSettings passwordLoginEnabled={passwordLoginEnabled.value} />
			{/if}
		</Card.Content>
	</Card.Root>
</main>
