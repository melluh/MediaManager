import client from '$lib/api';
import type { AuditLogPage } from '$lib/api/api';
import { auditCategories, type AuditCategory } from '$lib/components/audit-log/audit-actions';

export const AUDIT_LOG_PAGE_SIZE = 50;

export type AuditLogFilters = {
	page: number;
	category: AuditCategory | null;
	userId: string | null;
};

/** The audit log filters in a page's search params (`?page=&category=&user=`). */
export function auditLogFilters(url: URL): AuditLogFilters {
	const page = Number(url.searchParams.get('page'));
	const category = url.searchParams.get('category');
	return {
		page: Number.isInteger(page) && page > 0 ? page : 1,
		category: category && category in auditCategories ? (category as AuditCategory) : null,
		userId: url.searchParams.get('user')
	};
}

export async function fetchAuditLog(
	fetch: typeof globalThis.fetch,
	filters: AuditLogFilters
): Promise<AuditLogPage | null> {
	const { data } = await client.GET('/api/v1/admin/audit-log', {
		fetch,
		params: {
			query: {
				user_id: filters.userId,
				category: filters.category,
				limit: AUDIT_LOG_PAGE_SIZE,
				offset: (filters.page - 1) * AUDIT_LOG_PAGE_SIZE
			}
		}
	});
	return data ?? null;
}
