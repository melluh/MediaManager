<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import { Skeleton } from '$lib/components/ui/skeleton';
</script>

<Card.Root class="flex flex-col">
	<Card.Header class="flex-row items-start justify-between gap-2 space-y-0 pb-2">
		<div class="flex min-w-0 flex-1 flex-col gap-2">
			<Skeleton class="h-4 w-20" />
			<Skeleton class="h-3 w-32" />
		</div>
		<Skeleton class="h-4 w-16 shrink-0" />
	</Card.Header>
	<Card.Content class="flex flex-1 flex-col gap-2 pt-2 text-sm">
		<div class="flex gap-1">
			<Skeleton class="h-5 w-14" />
			<Skeleton class="h-5 w-14" />
		</div>
		<div class="grid grid-cols-2 gap-2">
			{#each { length: 6 }}
				<Skeleton class="h-12 w-full rounded-lg" />
			{/each}
		</div>
	</Card.Content>
	<Card.Footer class="items-center gap-2">
		<Skeleton class="h-9 w-full" />
	</Card.Footer>
</Card.Root>
