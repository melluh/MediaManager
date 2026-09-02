export class MovieLoadError extends Error {
	constructor(readonly status: number) {
		super(
			status === 404
				? 'This movie could not be found. It may have been deleted.'
				: 'Failed to load this movie. Please try again.'
		);
	}
}
