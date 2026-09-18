/**
 * Shared vocabulary for the "availability badge" shown on movie/show detail
 * pages. `primary` states whether the media can be watched right now (and at
 * what quality/season range); `secondary` reports an in-flight download
 * independently, since a movie/show can be available *and* have another
 * quality/season downloading at the same time.
 */

export type AvailabilityTone = 'available' | 'downloading' | 'error' | 'neutral';

export interface AvailabilityBadgeInfo {
	label: string;
	tone: AvailabilityTone;
	/** Percentage complete (0-100), only ever set on a 'downloading' badge. */
	progress?: number | null;
}

export interface MediaAvailability {
	primary: AvailabilityBadgeInfo;
	secondary?: AvailabilityBadgeInfo;
}

/**
 * Overlays live download progress (from `/api/v1/torrent/mine`) onto an
 * already-computed availability, if any was found. Kept as a separate step
 * so the primary/secondary classification never depends on which user is
 * viewing the page - only the percentage shown does.
 */
export function withDownloadProgress(
	availability: MediaAvailability,
	progress: number | null | undefined
): MediaAvailability {
	if (!availability.secondary || progress == null) return availability;
	return { ...availability, secondary: { ...availability.secondary, progress } };
}
