<script lang="ts">
	import AppBrand from '$lib/components/app-brand.svelte';
	import { Separator } from '$lib/components/ui/separator/index.js';

	import background from '$lib/images/pawel-czerwinski-NTYYL9Eb9y8-unsplash.jpg?enhanced';
	import { resolve } from '$app/paths';
	import { setContext } from 'svelte';
	import type { AuthMetadata } from '$lib/api/api';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();

	// Resolved here instead of in `load` so the login chrome paints immediately even
	// when the backend is slow or down - see the note in `routes/dashboard/+layout.ts`.
	let metadata = $state<AuthMetadata | undefined>(undefined);
	let status = $state<'loading' | 'ready' | 'error'>('loading');

	setContext('authMetadata', () => metadata);
	setContext('authMetadataStatus', () => status);

	$effect(() => {
		const pending = data.loginData;
		let cancelled = false;
		status = 'loading';

		pending.then((result) => {
			if (cancelled) return;
			if (result.state === 'ok') {
				metadata = result.metadata;
				status = 'ready';
			} else {
				status = 'error';
			}
		});

		return () => {
			cancelled = true;
		};
	});
</script>

<div class="grid min-h-svh lg:grid-cols-2">
	<div class="flex flex-col gap-4 p-6 md:p-10">
		<header class="flex justify-center gap-2 md:justify-start">
			<a class="flex items-center gap-2" href={resolve('/', {})}>
				<AppBrand size="lg" />
			</a>
		</header>
		<main class="flex flex-1 items-center justify-center">
			<div class="w-full max-w-[90vw]">
				{@render children()}
			</div>
		</main>
		<div class="flex flex-col items-center justify-center gap-3 text-center">
			<a
				target="_blank"
				class="underline"
				href="https://maxdorninger.github.io/MediaManager/latest/troubleshooting/"
			>
				Trouble logging in?
			</a>
			<footer
				class="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-sm text-muted-foreground"
			>
				<a target="_blank" class="underline" href="https://github.com/maxdorninger/MediaManager"
					>GitHub</a
				>
				<Separator class="h-4" orientation="vertical" />
				<a target="_blank" class="underline" href="https://github.com/sponsors/maxdorninger"
					>Donate</a
				>
				<Separator class="h-4" orientation="vertical" />
				<a
					target="_blank"
					class="underline"
					href="https://unsplash.com/photos/blue-white-and-red-abstract-painting-NTYYL9Eb9y8"
				>
					Image Credit
				</a>
			</footer>
		</div>
	</div>
	<div class="relative hidden lg:block">
		<enhanced:img
			src={background}
			alt="background"
			class="absolute inset-0 h-full w-full rounded-l-3xl object-cover dark:brightness-[0.8]"
		/>
	</div>
</div>
