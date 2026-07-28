<script lang="ts">
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Label } from '$lib/components/ui/label/index.js';

	let {
		id,
		label,
		description,
		checked,
		onCheckedChange
	}: {
		id: string;
		label: string;
		description: string;
		checked: boolean;
		onCheckedChange: (checked: boolean) => void;
	} = $props();
</script>

<div class="flex items-center justify-between gap-4">
	<div>
		<Label class="block text-sm font-medium" for={id}>{label}</Label>
		<p class="text-sm text-muted-foreground">{description}</p>
	</div>
	<Switch {checked} {id} {onCheckedChange} />
</div>
