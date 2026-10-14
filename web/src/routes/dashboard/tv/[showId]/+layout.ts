import type { LayoutLoad } from './$types';
import client from '$lib/api';
import { validate as uuidValidate } from 'uuid';
import type { PublicShow, RichShowTorrent } from '$lib/api/api';
import { ShowLoadError } from './show-load-error';
import { getShowSeed } from '$lib/api/media-seed';

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

	const { data: torrents } = await client.GET('/api/v1/tv/shows/{show_id}/torrents', {
		fetch: fetch,
		params: { path: { show_id: show.id! } }
	});

	return { show, torrents: torrents as RichShowTorrent };
}

// Deliberately not awaited - the layout renders a loading state instead of blocking
// first paint. See `routes/dashboard/+layout.ts`. `seed` is the library list's copy
// of the show, if we came from there, so the hero can paint in the meantime.
export const load: LayoutLoad = ({ params, fetch }) => {
	return { seed: getShowSeed(params.showId), show: fetchDetails(params.showId, fetch) };
};
