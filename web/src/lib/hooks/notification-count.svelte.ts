import client from '$lib/api';

const POLL_INTERVAL_MS = 30000;

let unreadCount = $state(0);
let intervalId: ReturnType<typeof setInterval> | undefined;
let paused = false;

async function refresh() {
	if (paused) return;
	const { data: count } = await client.GET('/api/v1/notification/unread/count');
	if (count !== undefined) {
		unreadCount = count;
	}
}

/** Starts the background poll. Call once from a layout that lives for the whole session. */
function startPolling() {
	if (intervalId !== undefined) return;
	refresh();
	intervalId = setInterval(refresh, POLL_INTERVAL_MS);
}

export const notificationCount = {
	get unread() {
		return unreadCount;
	},
	set unread(value: number) {
		unreadCount = value;
	},
	startPolling,
	/** Suppresses the background poll while a page already keeps `unread` in sync itself. */
	pausePolling() {
		paused = true;
	},
	resumePolling() {
		paused = false;
	}
};
