<script lang="ts">
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import logo from '$lib/images/logo.svg';
	import { Button } from '$lib/components/ui/button/index.js';
	import {
		FileQuestion,
		Home,
		ServerCrash,
		ShieldAlert,
		TriangleAlert,
		Undo2
	} from 'lucide-svelte';

	const errorDisplayByStatus: Record<number, { icon: typeof FileQuestion; title: string }> = {
		403: { icon: ShieldAlert, title: 'Access denied' },
		404: { icon: FileQuestion, title: 'Page not found' }
	};
	const defaultErrorDisplay = { icon: TriangleAlert, title: 'An error occurred' };
	const serverErrorDisplay = { icon: ServerCrash, title: 'Something went wrong' };

	let status = $derived(page.status);
	let isServerError = $derived(status >= 500);

	let display = $derived(
		isServerError ? serverErrorDisplay : (errorDisplayByStatus[status] ?? defaultErrorDisplay)
	);
	let Icon = $derived(display.icon);
	let title = $derived(display.title);

	// Don't surface the thrown error message for server errors, it may contain internal server details.
	let description = $derived(isServerError ? undefined : page.error?.message);
</script>

<svelte:head>
	<title>{status} - MediaManager</title>
	<meta content="An error occurred while using MediaManager" name="description" />
</svelte:head>

<div class="relative min-h-svh">
	<header class="absolute inset-x-0 top-0 flex justify-center p-6 md:justify-start md:p-10">
		<a class="flex items-center gap-2" href={resolve('/', {})}>
			<img alt="MediaManager Logo" class="size-10" src={logo} />
			<span class="text-xl font-bold">Media Manager</span>
		</a>
	</header>

	<main class="flex min-h-svh flex-col items-center justify-center gap-12 p-6 text-center">
		<div class="flex flex-col items-center gap-4">
			<Icon class="size-16 text-muted-foreground" />
			<div>
				<p class="text-sm font-medium text-muted-foreground">Error {status}</p>
				<h1 class="mt-1 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
					{title}
				</h1>
			</div>
			{#if description}
				<p class="max-w-md text-muted-foreground">{description}</p>
			{/if}
		</div>

		<div class="mt-8 flex items-center gap-3">
			<Button onclick={() => history.back()} variant="outline">
				<Undo2 class="size-4" />
				Go back
			</Button>
			<Button href={resolve('/dashboard', {})}>
				<Home class="size-4" />
				Go to dashboard
			</Button>
		</div>
	</main>
</div>
