import type { PageLoad } from './$types';
import client from '$lib/api';

export const load: PageLoad = async ({ fetch }) => {
	const [tvShows, movies, ownTorrents] = await Promise.all([
		client.GET('/api/v1/tv/shows', { fetch: fetch }).then((res) => res.data),
		client.GET('/api/v1/movies', { fetch: fetch }).then((res) => res.data),
		client.GET('/api/v1/torrent/mine', { fetch: fetch }).then((res) => res.data ?? [])
	]);
	return { tvShows, movies, ownTorrents };
};
