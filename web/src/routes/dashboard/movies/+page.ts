import type { PageLoad } from './$types';
import client from '$lib/api';
import { getImportableMedia } from '$lib/api/importable';
import { userOf } from '$lib/api/user';

export const load: PageLoad = async ({ fetch, parent }) => {
	const { user } = await parent();
	return {
		movies: client.GET('/api/v1/movies', { fetch: fetch }).then((res) => {
			if (res.error) throw new Error('Failed to load movies');
			return res.data;
		}),
		// Chained off the pending user rather than awaited, so this load resolves
		// immediately and the page can paint its skeletons.
		importable: userOf(user).then((u) => (u?.is_superuser ? getImportableMedia(false, fetch) : []))
	};
};
