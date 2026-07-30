<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	import { hdrLabels } from '$lib/components/download-dialogs/torrent-format';

	let { hdrFlags, freeleech }: { hdrFlags: string[] | null | undefined; freeleech: boolean } =
		$props();
</script>

<div class="flex flex-wrap gap-1">
	{#each hdrFlags ?? [] as flag (flag)}
		<Badge variant="outline">{hdrLabels[flag] ?? flag}</Badge>
	{/each}
	{#if freeleech}
		<Badge variant="outline" class="text-green-500">Freeleech</Badge>
	{/if}
</div>
