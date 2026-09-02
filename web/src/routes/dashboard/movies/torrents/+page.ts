import type { PageLoad } from './$types';
import client from '$lib/api';

// Not awaited - the page renders a loading state instead of blocking first paint.
// See `routes/dashboard/+layout.ts`.
export const load: PageLoad = ({ fetch }) => {
	return {
		torrents: client.GET('/api/v1/movies/torrents', { fetch: fetch }).then((res) => res.data)
	};
};
