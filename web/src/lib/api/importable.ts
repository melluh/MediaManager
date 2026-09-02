import client from '$lib/api';
import type { MediaImportSuggestion, MetaDataProviderSearchResult } from '$lib/api/api';
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

// The search results for one importable directory, fetched only when the user
// wants to correct the single match the scan already resolved. Returns null if
// the request failed, which the caller has to distinguish from "no results".
export async function getImportCandidates(
	isShow: boolean,
	directory: string
): Promise<MetaDataProviderSearchResult[] | null> {
	const { data, error } = isShow
		? await client.GET('/api/v1/tv/importable/candidates', {
				params: { query: { directory } }
			})
		: await client.GET('/api/v1/movies/importable/candidates', {
				params: { query: { directory } }
			});
	if (error) return null;
	return data ?? [];
}

// Imports a directory as the given media: the media item has to be added to
// the library first, since importing addresses it by its internal id. Reloads
// this route's data afterwards, so the imported directory drops off the list.
//
// `invalidate` defaults to true; a bulk importer processing many directories
// in sequence passes false to avoid reloading (and reshuffling) the list
// between each import, then invalidates once after the whole batch finishes.
export async function importMatchedMedia(
	isShow: boolean,
	media: MetaDataProviderSearchResult,
	directory: string,
	{ invalidate = true }: { invalidate?: boolean } = {}
): Promise<boolean> {
	const metadataProvider = media.metadata_provider as 'tmdb' | 'tvdb';
	let errored;
	if (isShow) {
		const { data } = await client.POST('/api/v1/tv/shows', {
			params: { query: { metadata_provider: metadataProvider, show_id: media.external_id } }
		});
		const { error } = await client.POST('/api/v1/tv/importable/{show_id}', {
			params: { path: { show_id: data?.id ?? 'no_id' }, query: { directory } }
		});
		errored = error;
	} else {
		const { data } = await client.POST('/api/v1/movies', {
			params: { query: { metadata_provider: metadataProvider, movie_id: media.external_id } }
		});
		const { error } = await client.POST('/api/v1/movies/importable/{movie_id}', {
			params: { path: { movie_id: data?.id ?? 'no_id' }, query: { directory } }
		});
		errored = error;
	}
	if (invalidate) await invalidateAll();
	return !!errored;
}
