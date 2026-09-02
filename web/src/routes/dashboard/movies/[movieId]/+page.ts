import type { PageLoad } from './$types';
import client from '$lib/api';
import { goto } from '$app/navigation';
import { resolve } from '$app/paths';
import { validate as uuidValidate } from 'uuid';
import type { PublicMovie, PublicMovieFile } from '$lib/api/api';
import { MovieLoadError } from './movie-load-error';

export type MovieDetails = { movie: PublicMovie; movieFiles: PublicMovieFile[] };

async function fetchDetails(
	movieId: string,
	fetch: typeof globalThis.fetch
): Promise<MovieDetails> {
	const byId = uuidValidate(movieId);
	const { data: movie, response } = byId
		? await client.GET('/api/v1/movies/{movie_id}', {
				fetch: fetch,
				params: { path: { movie_id: movieId } }
			})
		: await client.GET('/api/v1/movies/slug/{slug}', {
				fetch: fetch,
				params: { path: { slug: movieId } }
			});

	if (!movie) {
		throw new MovieLoadError(response.status);
	}

	// Canonicalise UUID urls onto the slug. This used to be a `redirect()` thrown from
	// `load`; now that the fetch is deferred it has to be a client-side navigation.
	if (byId && movie.slug) {
		goto(resolve('/dashboard/movies/[movieId]', { movieId: movie.slug }), { replaceState: true });
	}

	const { data: movieFiles } = await client.GET('/api/v1/movies/{movie_id}/files', {
		fetch: fetch,
		params: { path: { movie_id: movie.id! } }
	});

	return { movie, movieFiles: movieFiles ?? [] };
}

// Deliberately not awaited - the page renders a loading state instead of blocking
// first paint. See `routes/dashboard/+layout.ts`.
export const load: PageLoad = ({ params, fetch }) => {
	return { details: fetchDetails(params.movieId, fetch) };
};
