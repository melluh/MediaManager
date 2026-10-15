import client from '$lib/api';

// Ratings are a signed scale centered on 0 (the backend allows -2..2): negative
// means disliked, positive liked, and the further from 0 the stronger.
export const SUPER_LIKE = 2;
export const LIKE = 1;
export const DISLIKE = -1;
export const SUPER_DISLIKE = -2;

/** The ratings offered in the UI, as a scale from most positive to most negative. */
export const RATING_OPTIONS = [
	{ score: SUPER_LIKE, label: 'Loved it' },
	{ score: LIKE, label: 'Liked it' },
	{ score: DISLIKE, label: 'Disliked it' },
	{ score: SUPER_DISLIKE, label: 'Hated it' }
] as const;

/** Why a title is recommended, given the user's rating of the title it's credited to. */
export function recommendationReason(becauseOf: string, becauseScore: number | null): string {
	if (becauseScore === null) return `Because you watched ${becauseOf}`;
	return becauseScore >= SUPER_LIKE
		? `Because you loved ${becauseOf}`
		: `Because you liked ${becauseOf}`;
}

export async function fetchRating(mediaId: string, isShow: boolean): Promise<number | null> {
	const { data } = isShow
		? await client.GET('/api/v1/ratings/shows/{show_id}', {
				params: { path: { show_id: mediaId } }
			})
		: await client.GET('/api/v1/ratings/movies/{movie_id}', {
				params: { path: { movie_id: mediaId } }
			});
	return data?.score ?? null;
}

/** Sets the current user's rating, or clears it when `score` is null. Throws on failure. */
export async function saveRating(
	mediaId: string,
	isShow: boolean,
	score: number | null
): Promise<void> {
	const { response } = isShow
		? score === null
			? await client.DELETE('/api/v1/ratings/shows/{show_id}', {
					params: { path: { show_id: mediaId } }
				})
			: await client.PUT('/api/v1/ratings/shows/{show_id}', {
					params: { path: { show_id: mediaId } },
					body: { score }
				})
		: score === null
			? await client.DELETE('/api/v1/ratings/movies/{movie_id}', {
					params: { path: { movie_id: mediaId } }
				})
			: await client.PUT('/api/v1/ratings/movies/{movie_id}', {
					params: { path: { movie_id: mediaId } },
					body: { score }
				});
	if (!response.ok) throw new Error(`Saving rating failed: ${response.status}`);
}
