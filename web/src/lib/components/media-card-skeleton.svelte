<script lang="ts">
	import * as Card from '$lib/components/ui/card/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton';

	let { pulsating = true }: { pulsating?: boolean } = $props();
</script>

<Card.Root class="col-span-full overflow-hidden sm:col-span-1">
	<Skeleton class="aspect-2/3 w-full rounded-none {pulsating ? '' : 'animate-none'}" />
</Card.Root>
