import type { PageLoad } from './$types';
import client from '$lib/api';

export const load: PageLoad = async ({ fetch, parent }) => {
	const { user } = await parent();

	const users = user?.is_superuser
		? (await client.GET('/api/v1/users/all', { fetch: fetch })).data
		: [];

	const { data: authMetadata } = await client.GET('/api/v1/auth/metadata', { fetch: fetch });

	return {
		users,
		passwordLoginEnabled: authMetadata?.password_login_enabled ?? true
	};
};
