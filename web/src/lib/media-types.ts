import { resolve } from '$app/paths';
import type { MediaType } from '$lib/api/api.d.ts';

/**
 * Maps a search result's media_type to its detail-page route. Extend this
 * map (and the backend's MediaType enum / SearchService) when a new media
 * type becomes searchable.
 */
const MEDIA_TYPE_ROUTES: Record<MediaType, (slug: string) => string> = {
	movie: (slug) => resolve('/dashboard/movies/[movieId]', { movieId: slug }),
	tv: (slug) => resolve('/dashboard/tv/[showId]', { showId: slug })
};

const MEDIA_TYPE_LABELS: Record<MediaType, string> = {
	movie: 'Movie',
	tv: 'TV Show'
};

export function getMediaTypeHref(mediaType: MediaType, slug: string): string | undefined {
	return MEDIA_TYPE_ROUTES[mediaType]?.(slug);
}

export function getMediaTypeLabel(mediaType: MediaType): string {
	return MEDIA_TYPE_LABELS[mediaType] ?? mediaType;
}
