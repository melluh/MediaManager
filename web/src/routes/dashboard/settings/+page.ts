import type { PageLoad } from './$types';
import client from '$lib/api';
import { userOf } from '$lib/api/user';

// Nothing is awaited here - the page renders a loading state instead of blocking
// first paint. See `routes/dashboard/+layout.ts`.
export const load: PageLoad = async ({ fetch, parent }) => {
	const { user } = await parent();

	return {
		users: userOf(user).then(async (u) =>
			u?.is_superuser ? ((await client.GET('/api/v1/users/all', { fetch: fetch })).data ?? []) : []
		),
		passwordLoginEnabled: client
			.GET('/api/v1/auth/metadata', { fetch: fetch })
			.then((res) => res.data?.password_login_enabled ?? true)
	};
};
