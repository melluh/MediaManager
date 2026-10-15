import { MediaQuery } from 'svelte/reactivity';
import type { CarouselOptions } from '$lib/components/ui/carousel/context.js';

/**
 * Carousel `opts` that scroll freely on phones and tablets instead of snapping
 * to slide boundaries - align only controls where snap points land, so it
 * can't disable snapping by itself - and align-start snap on desktop.
 *
 * "Desktop" matches the carousels' `lg:pointer-fine:` classes: the prev/next
 * buttons only show there, so everywhere else is swiped and peeks a partial
 * card at the edge instead.
 */
export class ResponsiveCarouselOpts {
	#isDesktop = new MediaQuery('(min-width: 1024px) and (pointer: fine)');

	opts = $derived.by(
		(): CarouselOptions => (this.#isDesktop.current ? { align: 'start' } : { dragFree: true })
	);
}
