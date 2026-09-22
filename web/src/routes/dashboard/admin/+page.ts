import type { PageLoad } from './$types';
import client from '$lib/api';
import { userOf } from '$lib/api/user';
import type { DiskUsageStats, LibraryStats, UserRead } from '$lib/api/api';

// Nothing is awaited here - the page renders a loading state instead of blocking
// first paint. See `routes/dashboard/+layout.ts`.
export const load: PageLoad = async ({ fetch, parent }) => {
	const { user } = await parent();
	const isAdmin = userOf(user).then((u) => u?.is_superuser ?? false);

	return {
		stats: isAdmin.then(
			async (ok): Promise<LibraryStats | null> =>
				(ok && (await client.GET('/api/v1/admin/stats', { fetch: fetch })).data) || null
		),
		diskUsage: isAdmin.then(
			async (ok): Promise<DiskUsageStats | null> =>
				(ok && (await client.GET('/api/v1/admin/disk-usage', { fetch: fetch })).data) || null
		),
		users: isAdmin.then(
			async (ok): Promise<UserRead[]> =>
				(ok && (await client.GET('/api/v1/users/all', { fetch: fetch })).data) || []
		),
		passwordLoginEnabled: client
			.GET('/api/v1/auth/metadata', { fetch: fetch })
			.then((res) => res.data?.password_login_enabled ?? true)
	};
};
