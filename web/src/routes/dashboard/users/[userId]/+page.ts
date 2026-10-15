import type { PageLoad } from './$types';
import client from '$lib/api';
import { userOf } from '$lib/api/user';
import type { UserProfile, UserRead } from '$lib/api/api';

// Nothing is awaited here - the page renders a loading state instead of blocking
// first paint. See `routes/dashboard/+layout.ts`.
export const load: PageLoad = async ({ fetch, parent, params }) => {
	const { user } = await parent();
	const me = userOf(user);
	const isAdmin = me.then((u) => u?.is_superuser ?? false);

	return {
		isAdmin,
		currentUserId: me.then((u) => u?.id ?? null),
		passwordLoginEnabled: client
			.GET('/api/v1/auth/metadata', { fetch: fetch })
			.then((res) => res.data?.password_login_enabled ?? true),
		// Admins get the full user, for the edit dialog; everyone else only the profile.
		user: isAdmin.then(
			async (ok): Promise<UserRead | UserProfile | null> =>
				(ok
					? await client.GET('/api/v1/users/{id}', {
							fetch: fetch,
							params: { path: { id: params.userId } }
						})
					: await client.GET('/api/v1/users/{user_id}/profile', {
							fetch: fetch,
							params: { path: { user_id: params.userId } }
						})
				).data ?? null
		)
	};
};
