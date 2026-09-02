import type { LayoutLoad } from './$types';
import client from '$lib/api';
import type { UserResult } from '$lib/api/user';

/**
 * The current user is deliberately *not* awaited here: this app is a client-rendered
 * SPA, so anything a `load` awaits blocks the very first paint. Returning the pending
 * promise lets the layout mount immediately and render a loading indicator (and a
 * retryable error) instead of leaving the user on a blank page while /users/me hangs.
 *
 * The promise never rejects - a rejected, un-awaited promise would surface as an
 * unhandled rejection - it resolves to a discriminated result instead.
 */
export const load: LayoutLoad = ({ fetch }) => {
	const user: Promise<UserResult> = client
		.GET('/api/v1/users/me', { fetch: fetch })
		.then(({ data, error, response }) => {
			if (error || !data) {
				if (response.status === 401) {
					return { state: 'unauthorized' } as const;
				}
				console.error(`Failed to fetch current user, backend returned status ${response.status}`);
				return { state: 'unreachable', status: response.status } as const;
			}
			return { state: 'ok', user: data } as const;
		})
		.catch((e) => {
			console.error('Failed to fetch current user', e);
			return { state: 'unreachable', status: 0 } as const;
		});

	return { user };
};
