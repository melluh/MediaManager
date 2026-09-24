<script lang="ts">
	let { value, label }: { value: number | string; label: string } = $props();
</script>

<div class="rounded-lg border p-4 text-center">
	<p class="text-3xl font-bold">{value}</p>
	<p class="text-sm text-muted-foreground">{label}</p>
</div>
