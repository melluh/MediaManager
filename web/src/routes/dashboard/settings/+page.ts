import type { PageLoad } from './$types';
import client from '$lib/api';

export const load: PageLoad = async ({ fetch, parent }) => {
	const { user } = await parent();

	const users = user?.is_superuser
		? (await client.GET('/api/v1/users/all', { fetch: fetch })).data
		: [];

	return {
		users
	};
};
