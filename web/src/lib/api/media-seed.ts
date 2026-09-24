import type { MovieListItem, ShowSummary } from '$lib/api/api';

// Library list items handed to the detail page, so it can paint the hero
// straight away instead of a spinner. The list payload is a subset of the
// detail one (no torrents/seasons), so the detail page still fetches in the
// background - this only fills the gap until it lands.
const movieSeeds = new Map<string, MovieListItem>();
const showSeeds = new Map<string, ShowSummary>();

function fill<T extends MovieListItem | ShowSummary>(seeds: Map<string, T>, items: T[]) {
	// Replaced wholesale so media deleted since the last list load isn't
	// resurrected as a stale hero.
	seeds.clear();
	for (const item of items) {
		// Keyed by both, since detail urls may still carry the id.
		if (item.slug) seeds.set(item.slug, item);
		if (item.id) seeds.set(item.id, item);
	}
}

export function seedMovies(items: MovieListItem[]) {
	fill(movieSeeds, items);
}

export function seedShows(items: ShowSummary[]) {
	fill(showSeeds, items);
}

export function getMovieSeed(slugOrId: string): MovieListItem | undefined {
	return movieSeeds.get(slugOrId);
}

export function getShowSeed(slugOrId: string): ShowSummary | undefined {
	return showSeeds.get(slugOrId);
}
