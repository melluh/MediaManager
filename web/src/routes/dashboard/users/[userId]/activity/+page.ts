import type { PageLoad } from './$types';
import client from '$lib/api';
import { userOf } from '$lib/api/user';
import { auditLogFilters, fetchAuditLog } from '$lib/api/audit-log';
import type { AuditLogPage, UserProfile } from '$lib/api/api';

// Nothing is awaited here - the page renders a loading state instead of blocking
// first paint. See `routes/dashboard/+layout.ts`.
export const load: PageLoad = async ({ fetch, parent, params, url }) => {
	const { user } = await parent();
	const isAdmin = userOf(user).then((u) => u?.is_superuser ?? false);
	const filters = { ...auditLogFilters(url), userId: params.userId };

	return {
		filters,
		user: client
			.GET('/api/v1/users/{user_id}/profile', {
				fetch: fetch,
				params: { path: { user_id: params.userId } }
			})
			.then((res): UserProfile | null => res.data ?? null),
		log: isAdmin.then(
			async (ok): Promise<AuditLogPage | null> =>
				(ok && (await fetchAuditLog(fetch, filters))) || null
		)
	};
};
