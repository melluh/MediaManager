import { toast } from 'svelte-sonner';

/** Copies text to the clipboard and exposes a `copied` flag that resets itself. */
export class Clipboard {
	copied = $state(false);
	#resetTimer: ReturnType<typeof setTimeout> | undefined;
	#resetAfterMs: number;

	constructor(resetAfterMs = 2000) {
		this.#resetAfterMs = resetAfterMs;
	}

	async copy(text: string) {
		try {
			// `navigator.clipboard` is undefined when the app is served over plain
			// http, which is common for self-hosted setups on a LAN.
			await navigator.clipboard.writeText(text);
		} catch {
			toast.error('Could not copy to the clipboard.');
			return;
		}
		this.copied = true;
		clearTimeout(this.#resetTimer);
		this.#resetTimer = setTimeout(() => (this.copied = false), this.#resetAfterMs);
	}
}
