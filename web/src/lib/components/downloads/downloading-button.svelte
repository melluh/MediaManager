<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import { Progress } from '$lib/components/ui/progress/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import Users from '@lucide/svelte/icons/users';
	import Gauge from '@lucide/svelte/icons/gauge';
	import type { DownloadProgress } from '$lib/api/api';
	import { formatDownloadSpeed } from '$lib/utils';

	// Undefined when the download wasn't started by this user, or the download
	// client doesn't report progress: the button then shows without a percentage.
	let { progress }: { progress?: DownloadProgress | null } = $props();

	let percent = $derived(progress?.progress);
	let speedLabel = $derived(formatDownloadSpeed(progress?.download_speed_bytes_per_second));
</script>

<!-- Disabled in place of the download action, so a second download isn't
     started while one is running. -->
<Tooltip.Root disableHoverableContent>
	<Tooltip.Trigger>
		{#snippet child({ props })}
			<span {...props} class="inline-block">
				<Button disabled class="relative overflow-hidden bg-blue-600 text-white hover:bg-blue-600">
					Downloading{percent != null ? ` ${Math.round(percent)}%` : ''}
					<LoaderCircle class="animate-spin" />
					{#if percent != null}
						<Progress
							value={percent}
							class="absolute inset-x-0 bottom-0 h-1 rounded-none bg-transparent"
						/>
					{/if}
				</Button>
			</span>
		{/snippet}
	</Tooltip.Trigger>
	<Tooltip.Content>
		<div class="flex items-center gap-1.5 whitespace-nowrap">
			<Users class="size-3.5" />
			{progress?.seeders ?? '?'}
			<span>&middot;</span>
			<Gauge class="size-3.5" />
			{speedLabel ?? 'unknown'}
		</div>
	</Tooltip.Content>
</Tooltip.Root>
