import { createContext } from 'svelte';
import type {
	AuthMetadata,
	PublicShow,
	RichShowTorrent,
	UserReadWithPermissions
} from '$lib/api/api';

export type LoadStatus = 'loading' | 'ready' | 'error';

export interface Crumb {
	label: string;
	href?: string;
}

// The signed-in user, provided by the dashboard layout. It's undefined only
// while the layout is still resolving it.
const [getUserGetter, setUserContext] = createContext<() => UserReadWithPermissions | undefined>();
export { setUserContext };

/**
 * For components that render before the dashboard layout has resolved the
 * user (the sidebar and header), so they have to handle it being undefined.
 */
export function getMaybeCurrentUser(): () => UserReadWithPermissions | undefined {
	return getUserGetter();
}

/** For dashboard pages, which only render once the user is resolved. */
export function getCurrentUser(): () => UserReadWithPermissions {
	const get = getUserGetter();
	return () => get()!;
}

const [getCrumbSetter, setCrumbSetter] = createContext<(crumbs: Crumb[]) => void>();
export { setCrumbSetter };

/**
 * Sets the dashboard header's breadcrumbs for the current page. Pass a
 * function to keep them in sync with reactive state (e.g. a media name).
 */
export function setCrumbs(crumbs: Crumb[] | (() => Crumb[])) {
	const set = getCrumbSetter();
	$effect(() => {
		set(typeof crumbs === 'function' ? crumbs() : crumbs);
	});
}

// Set by pages with a hero backdrop behind the header: forces white header
// text/icons and hides the mobile logo while the backdrop is showing.
export const [getHeroHeaderSetter, setHeroHeaderSetter] =
	createContext<(active: boolean) => void>();

// Provided by the show layout, which resolves the show without blocking
// first paint. Children only render once both are loaded.
export const [getShowContext, setShowContext] = createContext<{
	show: () => PublicShow;
	torrents: () => RichShowTorrent;
}>();

// Provided by the login layout.
export const [getAuthMetadataContext, setAuthMetadataContext] = createContext<{
	metadata: () => AuthMetadata | undefined;
	status: () => LoadStatus;
}>();
