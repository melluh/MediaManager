/**
 * Calls `fn` every `intervalMs` while the component is mounted. Ticks are
 * skipped while the tab is hidden or while the previous call is still in
 * flight, and errors are swallowed so the next tick simply retries.
 *
 * Reactive state read synchronously by `fn` (e.g. a media id in the request
 * params) restarts the poll, so it follows the page to new data. Polling only
 * runs while `enabled` returns true.
 */
export function poll(
	fn: () => Promise<unknown>,
	intervalMs: number,
	{ enabled = () => true, immediate = true }: { enabled?: () => boolean; immediate?: boolean } = {}
) {
	$effect(() => {
		if (!enabled()) return;

		let inFlight = false;
		async function tick(force = false) {
			if (inFlight || (!force && document.hidden)) return;
			inFlight = true;
			try {
				await fn();
			} catch {
				// keep showing the last known state; the next tick will retry
			} finally {
				inFlight = false;
			}
		}

		if (immediate) tick(true);
		const handle = setInterval(tick, intervalMs);
		return () => clearInterval(handle);
	});
}
