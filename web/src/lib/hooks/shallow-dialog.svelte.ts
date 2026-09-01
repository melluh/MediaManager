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
				history.back();
			}
		}
	};
}
