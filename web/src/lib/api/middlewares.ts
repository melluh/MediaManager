import { handleLogout } from '$lib/utils.ts';
import type { Middleware } from 'openapi-fetch';

export const autoLogoutMiddleware: Middleware = {
	async onResponse({ request, response }) {
		if (response.status === 401 && !request.url.endsWith('/auth/cookie/logout')) {
			console.log(`Request to ${request.url} returned HTTP Error Code 401, logging out...`);
			await handleLogout();
		}
		if (response.status === 403) {
			console.log(
				`Request to ${request.url} returned HTTP Error Code 403, this shouldn't happen, consider opening a bug report!`
			);
		}
		return response;
	}
};
