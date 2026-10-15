<script lang="ts" module>
	const SIZE = 80;
	const C = SIZE / 2;

	// FNV-1a, to turn any user ID into a 32-bit seed.
	function hash(input: string): number {
		let h = 0x811c9dc5;
		for (let i = 0; i < input.length; i++) {
			h ^= input.charCodeAt(i);
			h = Math.imul(h, 0x01000193) >>> 0;
		}
		return h;
	}

	// mulberry32: a tiny seeded PRNG, so every user gets the same sequence of choices.
	function rng(seed: number): () => number {
		let a = seed;
		return () => {
			a = (a + 0x6d2b79f5) | 0;
			let t = Math.imul(a ^ (a >>> 15), 1 | a);
			t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
			return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
		};
	}

	type Accent = 'triangle' | 'square' | 'ring';

	/** An abstract, Bauhaus-like composition: a background, a diagonal band, a circle and an accent shape. */
	function avatar(seed: string) {
		const r = rng(hash(seed));
		const between = (min: number, max: number) => min + r() * (max - min);
		const pick = <T,>(items: T[]): T => items[Math.floor(r() * items.length)]!;

		// A small harmony around one base hue: the base, a neighbour, a contrast and a pale tint.
		const hue = r() * 360;
		const colors = [
			`hsl(${hue} 62% 52%)`,
			`hsl(${(hue + between(25, 50)) % 360} 70% 68%)`,
			`hsl(${(hue + between(150, 210)) % 360} 55% 38%)`,
			`hsl(${(hue + between(-30, 30) + 360) % 360} 80% 88%)`
		];
		for (let i = colors.length - 1; i > 0; i--) {
			const j = Math.floor(r() * (i + 1));
			[colors[i], colors[j]] = [colors[j]!, colors[i]!];
		}

		return {
			background: colors[0]!,
			band: {
				y: C + between(-14, 14),
				height: between(18, 34),
				angle: between(0, 180),
				color: colors[1]!
			},
			circle: {
				cx: between(18, 62),
				cy: between(18, 62),
				r: between(12, 22),
				color: colors[2]!
			},
			accent: {
				kind: pick<Accent>(['triangle', 'square', 'ring']),
				x: between(20, 60),
				y: between(20, 60),
				size: between(10, 18),
				angle: between(0, 360),
				color: colors[3]!
			}
		};
	}
</script>

<script lang="ts">
	import { cn } from '$lib/utils.js';

	let { userId, class: className }: { userId: string; class?: string } = $props();

	const a = $derived(avatar(userId));
</script>

<svg
	viewBox="0 0 {SIZE} {SIZE}"
	class={cn('size-8 shrink-0 overflow-hidden rounded-full', className)}
	aria-hidden="true"
>
	<rect width={SIZE} height={SIZE} fill={a.background} />
	<rect
		x={-SIZE}
		y={a.band.y - a.band.height / 2}
		width={SIZE * 3}
		height={a.band.height}
		fill={a.band.color}
		transform="rotate({a.band.angle} {C} {C})"
	/>
	<circle cx={a.circle.cx} cy={a.circle.cy} r={a.circle.r} fill={a.circle.color} />
	<g transform="translate({a.accent.x} {a.accent.y}) rotate({a.accent.angle})">
		{#if a.accent.kind === 'triangle'}
			<polygon
				points="0,{-a.accent.size} {a.accent.size * 0.87},{a.accent.size / 2} {-a.accent.size *
					0.87},{a.accent.size / 2}"
				fill={a.accent.color}
			/>
		{:else if a.accent.kind === 'square'}
			<rect
				x={-a.accent.size / 2}
				y={-a.accent.size / 2}
				width={a.accent.size}
				height={a.accent.size}
				fill={a.accent.color}
			/>
		{:else}
			<circle r={a.accent.size / 2} fill="none" stroke={a.accent.color} stroke-width="4" />
		{/if}
	</g>
</svg>
