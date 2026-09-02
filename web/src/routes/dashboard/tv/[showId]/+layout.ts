import type { LayoutLoad } from './$types';
import client from '$lib/api';
import { goto } from '$app/navigation';
import { resolve } from '$app/paths';
import { validate as uuidValidate } from 'uuid';
import type { PublicShow, RichShowTorrent } from '$lib/api/api';
import { ShowLoadError } from './show-load-error';

export type ShowDetails = { show: PublicShow; torrents: RichShowTorrent };

async function fetchDetails(showId: string, fetch: typeof globalThis.fetch): Promise<ShowDetails> {
	const byId = uuidValidate(showId);
	const { data: show, response } = byId
		? await client.GET('/api/v1/tv/shows/{show_id}', {
				fetch: fetch,
				params: { path: { show_id: showId } }
			})
		: await client.GET('/api/v1/tv/shows/slug/{slug}', {
				fetch: fetch,
				params: { path: { slug: showId } }
			});

	if (!show) {
		throw new ShowLoadError(response.status);
	}

	// Canonicalise UUID urls onto the slug. This used to be a `redirect()` thrown from
	// `load`; now that the fetch is deferred it has to be a client-side navigation.
	if (byId && show.slug) {
		goto(resolve('/dashboard/tv/[showId]', { showId: show.slug }), { replaceState: true });
	}

	const { data: torrents } = await client.GET('/api/v1/tv/shows/{show_id}/torrents', {
		fetch: fetch,
		params: { path: { show_id: show.id! } }
	});

	return { show, torrents: torrents as RichShowTorrent };
}

// Deliberately not awaited - the layout renders a loading state instead of blocking
// first paint. See `routes/dashboard/+layout.ts`.
export const load: LayoutLoad = ({ params, fetch }) => {
	return { show: fetchDetails(params.showId, fetch) };
};
