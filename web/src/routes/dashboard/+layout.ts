import type { LayoutLoad } from './$types';
import { error as httpError } from '@sveltejs/kit';
import { resolve } from '$app/paths';
import { goto } from '$app/navigation';
import client from '$lib/api';

export const load: LayoutLoad = async ({ fetch }) => {
	const { data, error, response } = await client.GET('/api/v1/users/me', { fetch: fetch });

	if (error) {
		if (response.status === 401) {
			console.log('unauthorized, redirecting to login');
			await goto(resolve('/login', {}));
			return { user: undefined };
		}
		// Non-auth failure (e.g. backend still starting up after a restart) - don't treat this
		// as "not verified", show the generic retryable error page instead.
		console.error(`Failed to fetch current user, backend returned status ${response.status}`);
		throw httpError(503, 'Could not reach the MediaManager backend. Please try again in a moment.');
	}
	return { user: data };
};
