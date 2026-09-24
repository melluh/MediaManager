import type { UserReadWithPermissions } from '$lib/api/api';

export type UserResult =
	| { state: 'ok'; user: UserReadWithPermissions }
	| { state: 'unauthorized' }
	| { state: 'unreachable'; status: number };

/** Convenience for loads that only care about the user itself, not why it is missing. */
export function userOf(result: Promise<UserResult>): Promise<UserReadWithPermissions | undefined> {
	return result.then((r) => (r.state === 'ok' ? r.user : undefined));
}
