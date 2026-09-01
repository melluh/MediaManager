import client from '$lib/api';
import type { ServiceHealth } from '$lib/api/api';

const POLL_INTERVAL_MS = 60000;

let services = $state<ServiceHealth[]>([]);
let intervalId: ReturnType<typeof setInterval> | undefined;

async function refresh() {
	const { data } = await client.GET('/api/v1/health/services');
	if (data) {
		services = data.services;
	}
}

/** Starts the background poll. Call once from a layout that lives for the whole session. */
function startPolling() {
	if (intervalId !== undefined) return;
	refresh();
	intervalId = setInterval(refresh, POLL_INTERVAL_MS);
}

export const serviceHealth = {
	get services() {
		return services;
	},
	startPolling
};
