import { untrack } from 'svelte';
import type { LoadStatus } from '$lib/context.svelte';

/**
 * Resolves a promise from `load` data into local state, and re-resolves it
 * whenever `getPromise` returns a new one (e.g. after `invalidateAll()`).
 * Results from a promise that has since been replaced are ignored.
 *
 * With `keepPrevious` (the default), a refresh keeps the last value and the
 * `ready` status while the new promise is pending. Awaiting load promises
 * directly in markup would remount everything under the `{#await}` on each
 * refresh, wiping local state such as an open dialog.
 *
 * `key` identifies what the promise is for (e.g. a route param). The previous
 * value is only kept while the key stays the same, so navigating to other
 * media shows the loading state instead of the old media, while a refresh of
 * the same media updates in place.
 */
export class Resolved<T> {
	value: T | undefined = $state();
	error: unknown = $state();
	status: LoadStatus = $state('loading');
	#valueKey: unknown;

	constructor(
		getPromise: () => Promise<T>,
		{ keepPrevious = true, key }: { keepPrevious?: boolean; key?: () => unknown } = {}
	) {
		$effect(() => {
			const promise = getPromise();
			const currentKey = key?.();
			let cancelled = false;
			untrack(() => {
				if (!keepPrevious || this.status !== 'ready' || currentKey !== this.#valueKey) {
					this.status = 'loading';
				}
			});

			promise.then(
				(value) => {
					if (cancelled) return;
					this.value = value;
					this.#valueKey = currentKey;
					this.error = undefined;
					this.status = 'ready';
				},
				(error) => {
					if (cancelled) return;
					this.error = error;
					this.status = 'error';
				}
			);

			return () => {
				cancelled = true;
			};
		});
	}
}
