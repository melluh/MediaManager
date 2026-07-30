import type { IndexerQueryResult } from '$lib/api/api';

export interface SlotGroup {
	slotName: string;
	slotLabel: string;
	result: IndexerQueryResult;
}

export interface GroupedTorrents {
	heroPick: SlotGroup | null;
	otherPicks: SlotGroup[];
	allPicks: SlotGroup[];
	raw: IndexerQueryResult[];
}

/**
 * Groups a result list into the single overall top pick (the hero card),
 * every other slot's winner, and the full raw list. Picks the
 * highest-scoring result per slot_name directly (rather than trusting input
 * order) because some dialogs concatenate multiple independently-sorted
 * searches (one per selected episode/season) before this runs.
 */
export function groupIntoSlots(results: IndexerQueryResult[] | null | undefined): GroupedTorrents {
	const raw = results ?? [];
	const bestPerSlot = new Map<string, IndexerQueryResult>();

	for (const result of raw) {
		if (!result.slot_name) continue;
		const existing = bestPerSlot.get(result.slot_name);
		if (!existing || result.score > existing.score) {
			bestPerSlot.set(result.slot_name, result);
		}
	}

	const groups: SlotGroup[] = [...bestPerSlot.values()]
		.sort((a, b) => (a.slot_index ?? 0) - (b.slot_index ?? 0))
		.map((result) => ({
			slotName: result.slot_name as string,
			slotLabel: result.slot_label ?? (result.slot_name as string),
			result
		}));

	// Groups are already sorted by slot_index, so the first one is the
	// highest-priority slot - default to it.
	const heroPick = groups[0] ?? null;

	return {
		heroPick,
		otherPicks: heroPick ? groups.filter((g) => g.slotName !== heroPick.slotName) : groups,
		allPicks: groups,
		raw
	};
}
