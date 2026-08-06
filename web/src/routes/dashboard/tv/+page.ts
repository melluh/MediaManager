import type { PageLoad } from './$types';
import client from '$lib/api';

export const load: PageLoad = async ({ fetch }) => {
	return {
		tvShows: client.GET('/api/v1/tv/shows', { fetch: fetch }).then((res) => res.data)
	};
};
