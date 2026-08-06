<script lang="ts">
	import { navigating } from '$app/state';

	let progress = $state(0);
	let visible = $state(false);
	let growInterval: ReturnType<typeof setInterval> | undefined;
	let hideTimeout: ReturnType<typeof setTimeout> | undefined;

	$effect(() => {
		if (navigating.to) {
			clearInterval(growInterval);
			clearTimeout(hideTimeout);
			visible = true;
			progress = 15;
			growInterval = setInterval(() => {
				progress += (90 - progress) * 0.1;
			}, 100);
		} else {
			clearInterval(growInterval);
			progress = 100;
			hideTimeout = setTimeout(() => {
				visible = false;
				progress = 0;
			}, 200);
		}

		return () => {
			clearInterval(growInterval);
			clearTimeout(hideTimeout);
		};
	});
</script>

{#if visible}
	<div class="fixed top-0 left-0 z-50 h-0.5 w-full bg-transparent">
		<div
			class="h-full bg-primary transition-[width] duration-200 ease-out"
			style={`width: ${progress}%`}
		></div>
	</div>
{/if}
