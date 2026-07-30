import type { PageLoad } from './$types';
import client from '$lib/api';

export const load: PageLoad = async ({ fetch }) => {
	return {
		movies: await client.GET('/api/v1/movies', { fetch: fetch }).then((res) => res.data)
	};
};
