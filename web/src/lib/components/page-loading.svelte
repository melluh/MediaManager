<script lang="ts">
	import { Spinner } from '$lib/components/ui/spinner';

	let { message = 'Loading…', fullPage = false }: { message?: string; fullPage?: boolean } =
		$props();
</script>

<div
	class="flex flex-1 flex-col items-center justify-center gap-3 p-8 {fullPage
		? 'min-h-svh w-full'
		: 'min-h-64'}"
>
	<Spinner class="size-8 text-muted-foreground" />
	<p class="text-sm text-muted-foreground">{message}</p>
</div>
