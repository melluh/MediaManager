<script lang="ts">
	import { resolve } from '$app/paths';

	let { message }: { message: string } = $props();
</script>

<!--
	Mirrors the static #app-boot-splash in app.html so the transition from "app is
	booting" to "we're signing you in" reads as one continuous splash screen
	instead of a second, differently-styled loading screen.
-->
<div class="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-background">
	<img alt="" class="app-splash-logo h-[4.5rem] w-[4.5rem]" src={resolve('/logo.svg', {})} />
	<p class="text-lg font-semibold text-foreground">MediaManager</p>
	<div class="app-splash-spinner size-5 rounded-full border-2 border-muted-foreground"></div>
	<p class="text-sm text-muted-foreground">{message}</p>
</div>

<style>
	.app-splash-spinner {
		border-top-color: transparent;
		animation: app-splash-spin 0.8s linear infinite;
	}
	.app-splash-logo {
		animation: app-splash-pulse 1.8s ease-in-out infinite;
	}
	@keyframes app-splash-spin {
		to {
			transform: rotate(360deg);
		}
	}
	@keyframes app-splash-pulse {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.5;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.app-splash-spinner {
			animation-duration: 2s;
		}
		.app-splash-logo {
			animation: none;
		}
	}
</style>
