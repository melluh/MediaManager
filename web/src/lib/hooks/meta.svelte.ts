import client from '$lib/api';
import type { Meta } from '$lib/api/api';

// Static per backend process (it only changes with the config, i.e. on a
// restart), so it's fetched once per session and shared by everything that
// needs it, instead of each endpoint repeating it.
let current = $state<Meta | null>(null);
let pending: Promise<Meta | null> | undefined;

/** Fetches the instance metadata, at most once unless a previous attempt failed. */
function load(): Promise<Meta | null> {
	pending ??= client
		.GET('/api/v1/meta')
		.then(({ data }) => data ?? null)
		.catch(() => null)
		.then((data) => {
			current = data;
			// Let the next caller retry rather than caching a failure.
			if (data === null) pending = undefined;
			return data;
		});
	return pending;
}

export const meta = {
	/** The instance metadata, or null until it has loaded. */
	get current() {
		return current;
	},
	load
};
