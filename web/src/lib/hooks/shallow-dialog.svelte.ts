import { pushState } from '$app/navigation';
import { page } from '$app/state';

/**
 * Binds a dialog's open state to a shallow-routed history entry, so the
 * browser Back button closes the dialog instead of leaving the page.
 *
 * Dialogs are tracked as a stack (`page.state.dialogs`), so nested dialogs
 * (e.g. a confirmation dialog opened from within another dialog) close
 * innermost-first as the user presses Back. `key` must be unique among all
 * dialogs that can be open at once — components rendered in a loop (one
 * dialog per list item) must derive it from the item's id.
 *
 * Use `bind:open={() => d.open, (v) => (d.open = v)}` on the dialog.
 *
 * Don't use this for a dialog whose success action navigates away (e.g.
 * `goto()` after a delete) — just call `goto()` directly and skip setting
 * `open = false`; the navigation replaces the page (and its state) anyway,
 * and racing it against the async `history.back()` this uses to close is
 * unnecessary.
 */
let pendingClose: Promise<void> | null = null;

/**
 * Resolves once any dialog closed via `shallowDialog` has finished popping its
 * history entry. SvelteKit cancels in-flight invalidations on `popstate`, so a
 * `refreshAll()` started while a close is still pending is silently dropped —
 * await this first when refreshing right after closing a dialog.
 */
export function shallowDialogsSettled(): Promise<void> {
	return pendingClose ?? Promise.resolve();
}

export function shallowDialog(key: string) {
	return {
		get open() {
			return (page.state.dialogs ?? []).includes(key);
		},
		set open(value: boolean) {
			const stack = page.state.dialogs ?? [];
			if (value) {
				if (stack.includes(key)) return;
				pushState('', { ...page.state, dialogs: [...stack, key] });
			} else if (stack.includes(key)) {
				// SvelteKit's own popstate listener is registered first, so by the
				// time this resolves it has already handled the history change.
				const closed = new Promise<void>((resolve) =>
					addEventListener('popstate', () => resolve(), { once: true })
				);
				pendingClose = closed;
				closed.then(() => {
					if (pendingClose === closed) pendingClose = null;
				});
				history.back();
			}
		}
	};
}
