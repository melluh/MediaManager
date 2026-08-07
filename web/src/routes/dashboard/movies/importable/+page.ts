import type { PageLoad } from './$types';
import { getImportableMedia } from '$lib/api/importable';

export const load: PageLoad = async ({ fetch, parent }) => {
	const { user } = await parent();
	const importable = user?.is_superuser ? await getImportableMedia(false, fetch) : [];

	return { importable };
};
