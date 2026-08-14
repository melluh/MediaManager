import { useSidebar } from '$lib/components/ui/sidebar/index.js';
import type { CarouselOptions } from '$lib/components/ui/carousel/context.js';

/**
 * Carousel `opts` that scroll freely on mobile instead of snapping to slide
 * boundaries - align only controls where snap points land, so it can't
 * disable snapping by itself - and align-start snap on desktop.
 *
 * Reuses the sidebar's mobile-detection instance rather than opening a
 * second matchMedia listener for the same breakpoint, so - like useSidebar()
 * itself - this only works inside the dashboard's Sidebar.Provider, and must
 * be instantiated during a component's synchronous setup.
 */
export class ResponsiveCarouselOpts {
	#sidebar = useSidebar();

	opts = $derived.by(
		(): CarouselOptions => (this.#sidebar.isMobile ? { dragFree: true } : { align: 'start' })
	);
}
