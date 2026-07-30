import type { LayoutLoad } from './$types';
import client from '$lib/api';
import { error, redirect } from '@sveltejs/kit';
import { resolve } from '$app/paths';
import { validate as uuidValidate } from 'uuid';

function getShowTorrents(showId: string, fetch: typeof globalThis.fetch) {
	return client
		.GET('/api/v1/tv/shows/{show_id}/torrents', {
			fetch: fetch,
			params: { path: { show_id: showId } }
		})
		.then((x) => x.data);
}

export const load: LayoutLoad = async ({ params, fetch }) => {
	if (uuidValidate(params.showId)) {
		const { data: show, response } = await client.GET('/api/v1/tv/shows/{show_id}', {
			fetch: fetch,
			params: { path: { show_id: params.showId } }
		});
		if (!show) {
			if (response.status === 404) {
				error(404, 'This show could not be found. It may have been deleted.');
			}
			error(response.status, 'Failed to load this show. Please try again.');
		}
		if (show.slug) {
			redirect(301, resolve('/dashboard/tv/[showId]', { showId: show.slug }));
		}
		return {
			showData: show,
			torrentsData: await getShowTorrents(params.showId, fetch)
		};
	}

	const { data: show, response } = await client.GET('/api/v1/tv/shows/slug/{slug}', {
		fetch: fetch,
		params: { path: { slug: params.showId } }
	});

	if (!show) {
		if (response.status === 404) {
			error(404, 'This show could not be found. It may have been deleted.');
		}
		error(response.status, 'Failed to load this show. Please try again.');
	}

	return {
		showData: show,
		torrentsData: await getShowTorrents(show.id!, fetch)
	};
};
