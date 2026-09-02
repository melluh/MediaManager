import type { PageLoad } from './$types';
import { getImportableMedia } from '$lib/api/importable';
import { userOf } from '$lib/api/user';

export const load: PageLoad = async ({ fetch, parent }) => {
	const { user } = await parent();
	// Deliberately not awaited - the page renders a loading state instead of
	// blocking first paint. See `routes/dashboard/+layout.ts`.
	return {
		importable: userOf(user).then((u) => (u?.is_superuser ? getImportableMedia(false, fetch) : []))
	};
};
