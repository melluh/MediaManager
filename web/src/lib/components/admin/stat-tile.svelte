<script lang="ts">
	let { value, label }: { value: number | string; label: string } = $props();
</script>

<div class="rounded-lg border p-2 text-center md:p-4">
	<p class="text-2xl font-bold md:text-3xl">{value}</p>
	<p class="text-xs text-muted-foreground md:text-sm">{label}</p>
</div>
