// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
import type { MediaLibraryFilters } from '$lib/utils';

declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		interface PageState {
			// Stack of open shallow-routed dialog keys, innermost last. See
			// $lib/hooks/shallow-dialog.svelte.ts.
			dialogs?: string[];
			// Library filters for the current /dashboard/movies or /dashboard/tv
			// history entry, so they survive a round trip to a detail page and
			// back. See media-library-page.svelte.
			libraryFilters?: MediaLibraryFilters;
		}
		// interface Platform {}
	}
}

// Environment variables declarations
declare module '$env/dynamic/public' {
	export const env: {
		PUBLIC_API_URL: string;
		[key: string]: string | undefined;
	};
}

declare module '$env/static/public' {
	export const PUBLIC_VERSION: string;
	export const PUBLIC_API_URL: string;
}

// Enhanced image module declarations
declare module '*?enhanced' {
	const value: unknown;
	export default value;
}

export {};
