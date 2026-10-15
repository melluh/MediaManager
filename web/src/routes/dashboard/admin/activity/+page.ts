import type { PageLoad } from './$types';
import client from '$lib/api';
import { userOf } from '$lib/api/user';
import { auditLogFilters, fetchAuditLog } from '$lib/api/audit-log';
import type { AuditLogPage, UserRead } from '$lib/api/api';

// Nothing is awaited here - the page renders a loading state instead of blocking
// first paint. See `routes/dashboard/+layout.ts`.
export const load: PageLoad = async ({ fetch, parent, url }) => {
	const { user } = await parent();
	const isAdmin = userOf(user).then((u) => u?.is_superuser ?? false);
	const filters = auditLogFilters(url);

	return {
		filters,
		log: isAdmin.then(
			async (ok): Promise<AuditLogPage | null> =>
				(ok && (await fetchAuditLog(fetch, filters))) || null
		),
		users: isAdmin.then(
			async (ok): Promise<UserRead[]> =>
				(ok && (await client.GET('/api/v1/users/all', { fetch: fetch })).data) || []
		)
	};
};
