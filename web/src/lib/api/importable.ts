import client from '$lib/api';
import type { MediaImportSuggestion } from '$lib/api/api';
import { resolve } from '$app/paths';
import { invalidateAll } from '$app/navigation';

export function importablePath(isShow: boolean): string {
	return isShow
		? resolve('/dashboard/tv/importable', {})
		: resolve('/dashboard/movies/importable', {});
}

export async function getImportableMedia(
	isShow: boolean,
	fetchFn?: typeof fetch
): Promise<MediaImportSuggestion[]> {
	const { data } = isShow
		? await client.GET('/api/v1/tv/importable', { fetch: fetchFn })
		: await client.GET('/api/v1/movies/importable', { fetch: fetchFn });
	return data ?? [];
}

// Rescans on the backend and reloads this route's data (including any
// `getImportableMedia` results sourced from a `load` function) once it's done.
export async function rescanImportableMedia(isShow: boolean): Promise<boolean> {
	const { error } = isShow
		? await client.POST('/api/v1/tv/importable/rescan')
		: await client.POST('/api/v1/movies/importable/rescan');
	await invalidateAll();
	return !!error;
}
