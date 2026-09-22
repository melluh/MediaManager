import type { PageLoad } from './$types';
import client from '$lib/api';

export const load: PageLoad = async ({ fetch }) => {
	return {
		passwordLoginEnabled: client
			.GET('/api/v1/auth/metadata', { fetch: fetch })
			.then((res) => res.data?.password_login_enabled ?? true)
	};
};
