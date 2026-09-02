import type { UserRead } from '$lib/api/api';

export type UserResult =
	| { state: 'ok'; user: UserRead }
	| { state: 'unauthorized' }
	| { state: 'unreachable'; status: number };

/** Convenience for loads that only care about the user itself, not why it is missing. */
export function userOf(result: Promise<UserResult>): Promise<UserRead | undefined> {
	return result.then((r) => (r.state === 'ok' ? r.user : undefined));
}
