import { MediaQuery } from 'svelte/reactivity';

const MOBILE_BREAKPOINT = 768;
// Matches Tailwind's `lg` breakpoint: below it the dashboard uses the compact
// (mobile) header and the sidebar is an off-canvas sheet, like on phones.
const DESKTOP_BREAKPOINT = 1024;
// Landscape iPads are 1024-1376px wide, which overlaps small laptops, so touch
// screens up to this width also count as tablets for the sidebar.
const TOUCH_TABLET_MAX_WIDTH = 1440;

export class IsMobile extends MediaQuery {
	constructor() {
		super(`max-width: ${MOBILE_BREAKPOINT - 1}px`);
	}
}

export class IsTablet extends MediaQuery {
	constructor() {
		super(
			`(min-width: ${MOBILE_BREAKPOINT}px) and (max-width: ${DESKTOP_BREAKPOINT - 1}px), ` +
				`(min-width: ${MOBILE_BREAKPOINT}px) and (max-width: ${TOUCH_TABLET_MAX_WIDTH - 1}px) and (pointer: coarse)`
		);
	}
}
