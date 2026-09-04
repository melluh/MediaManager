export class ShowLoadError extends Error {
	constructor(readonly status: number) {
		super(
			status === 404
				? 'This show could not be found. It may have been deleted.'
				: 'Failed to load this show. Please try again.'
		);
	}
}
