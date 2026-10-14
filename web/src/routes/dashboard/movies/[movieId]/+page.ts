import type { PageLoad } from './$types';
import client from '$lib/api';
import { validate as uuidValidate } from 'uuid';
import type { PublicMovie, PublicMovieFile } from '$lib/api/api';
import { MovieLoadError } from './movie-load-error';
import { getMovieSeed } from '$lib/api/media-seed';

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

	const { data: movieFiles } = await client.GET('/api/v1/movies/{movie_id}/files', {
		fetch: fetch,
		params: { path: { movie_id: movie.id! } }
	});

	return { movie, movieFiles: movieFiles ?? [] };
}

// Deliberately not awaited - the page renders a loading state instead of blocking
// first paint. See `routes/dashboard/+layout.ts`. `seed` is the library list's copy
// of the movie, if we came from there, so the hero can paint in the meantime.
export const load: PageLoad = ({ params, fetch }) => {
	return { seed: getMovieSeed(params.movieId), details: fetchDetails(params.movieId, fetch) };
};
