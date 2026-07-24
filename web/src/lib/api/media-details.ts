import client from '$lib/api';
import type { MetaDataProviderSearchResult, Movie, Show } from '$lib/api/api';

// Shared so hovering an add-media-card can warm the cache before the dialog
// mounts and asks for the same details.
const cache = new Map<string, Promise<Show | Movie | null>>();

function cacheKey(result: MetaDataProviderSearchResult, isShow: boolean) {
	return `${isShow ? 'tv' : 'movie'}:${result.metadata_provider}:${result.external_id}:${result.original_language ?? ''}`;
}

async function fetchMediaDetails(
	result: MetaDataProviderSearchResult,
	isShow: boolean
): Promise<Show | Movie | null> {
	const params = {
		query: {
			metadata_provider: result.metadata_provider as 'tmdb' | 'tvdb',
			language: result.original_language ?? undefined
		}
	};
	if (isShow) {
		const { data } = await client.GET('/api/v1/tv/external/{show_id}', {
			params: { ...params, path: { show_id: result.external_id } }
		});
		return data ?? null;
	} else {
		const { data } = await client.GET('/api/v1/movies/external/{movie_id}', {
			params: { ...params, path: { movie_id: result.external_id } }
		});
		return data ?? null;
	}
}

export function fetchMediaDetailsCached(
	result: MetaDataProviderSearchResult,
	isShow: boolean
): Promise<Show | Movie | null> {
	const key = cacheKey(result, isShow);
	let pending = cache.get(key);
	if (!pending) {
		pending = fetchMediaDetails(result, isShow);
		cache.set(key, pending);
		// Don't cache failures - a hover-triggered prefetch failing silently
		// shouldn't permanently block the dialog from retrying the fetch.
		pending.catch(() => cache.delete(key));
	}
	return pending;
}
