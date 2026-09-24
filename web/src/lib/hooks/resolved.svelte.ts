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
 */
export class Resolved<T> {
	value: T | undefined = $state();
	error: unknown = $state();
	status: LoadStatus = $state('loading');

	constructor(getPromise: () => Promise<T>, { keepPrevious = true } = {}) {
		$effect(() => {
			const promise = getPromise();
			let cancelled = false;
			untrack(() => {
				if (!keepPrevious || this.status !== 'ready') this.status = 'loading';
			});

			promise.then(
				(value) => {
					if (cancelled) return;
					this.value = value;
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
