import type { PageLoad } from './$types';
import client from '$lib/api';
import { getImportableMedia } from '$lib/api/importable';

export const load: PageLoad = async ({ fetch, parent }) => {
	const { user } = await parent();
	return {
		movies: client.GET('/api/v1/movies', { fetch: fetch }).then((res) => res.data),
		importable: user?.is_superuser ? getImportableMedia(false, fetch) : Promise.resolve([])
	};
};
