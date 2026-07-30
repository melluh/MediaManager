import type { PageLoad } from './$types';
import client from '$lib/api';
import { error, redirect } from '@sveltejs/kit';
import { resolve } from '$app/paths';
import { validate as uuidValidate } from 'uuid';

function getMovieFiles(movieId: string, fetch: typeof globalThis.fetch) {
	return client
		.GET('/api/v1/movies/{movie_id}/files', {
			fetch: fetch,
			params: { path: { movie_id: movieId } }
		})
		.then((x) => x.data);
}

export const load: PageLoad = async ({ params, fetch }) => {
	if (uuidValidate(params.movieId)) {
		const { data: movie } = await client.GET('/api/v1/movies/{movie_id}', {
			fetch: fetch,
			params: { path: { movie_id: params.movieId } }
		});
		if (!movie) {
			error(404, 'This movie could not be found. It may have been deleted.');
		}
		if (movie.slug) {
			redirect(301, resolve('/dashboard/movies/[movieId]', { movieId: movie.slug }));
		}
		return {
			movie,
			movieFiles: await getMovieFiles(params.movieId, fetch)
		};
	}

	const { data: movie } = await client.GET('/api/v1/movies/slug/{slug}', {
		fetch: fetch,
		params: { path: { slug: params.movieId } }
	});

	if (!movie) {
		error(404, 'This movie could not be found. It may have been deleted.');
	}

	return {
		movie,
		movieFiles: await getMovieFiles(movie.id!, fetch)
	};
};
