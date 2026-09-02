import type { PageLoad } from './$types';
import client from '$lib/api';

// Nothing is awaited here - the page renders a loading state instead of blocking
// first paint. See `routes/dashboard/+layout.ts`.
export const load: PageLoad = ({ fetch, params }) => {
	return {
		season: client
			.GET('/api/v1/tv/seasons/{season_id}', {
				fetch: fetch,
				params: { path: { season_id: params.SeasonId } }
			})
			.then((x) => x.data),
		files: client
			.GET('/api/v1/tv/seasons/{season_id}/files', {
				fetch: fetch,
				params: { path: { season_id: params.SeasonId } }
			})
			.then((x) => x.data)
	};
};
