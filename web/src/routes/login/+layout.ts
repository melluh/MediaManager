import type { LayoutLoad } from './$types';
import client from '$lib/api';
import type { AuthMetadata } from '$lib/api/api';

export type AuthMetadataResult =
	| { state: 'ok'; metadata: AuthMetadata }
	| { state: 'unreachable'; status: number };

/**
 * Not awaited on purpose - see the note in `routes/dashboard/+layout.ts`. Awaiting
 * here meant a slow or unreachable backend left the login screen completely blank.
 */
export const load: LayoutLoad = ({ fetch }) => {
	const loginData: Promise<AuthMetadataResult> = client
		.GET('/api/v1/auth/metadata', { fetch: fetch })
		.then(({ data, response }) => {
			if (!response.ok || !data) {
				return { state: 'unreachable', status: response.status } as const;
			}
			return { state: 'ok', metadata: data } as const;
		})
		.catch((e) => {
			console.error('Failed to fetch auth metadata', e);
			return { state: 'unreachable', status: 0 } as const;
		});

	return { loginData };
};
