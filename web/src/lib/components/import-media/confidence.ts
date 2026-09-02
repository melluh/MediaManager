import type { ImportMatchConfidence } from '$lib/api/api';

export type ConfidenceMeta = {
	/** The badge's text. */
	label: string;
	/** Why the scan landed on this rating, shown on hover. */
	hint: string;
	/** Badge styling: loud for the ratings the user has to act on, quiet otherwise. */
	badgeClass: string;
	/** Row styling, so a long list can be skimmed for the rows that stand out. */
	rowClass: string;
	/** Whether the user should look at this row before importing it. */
	needsAttention: boolean;
	/** Lower sorts first, so the rows that need a decision lead the list. */
	rank: number;
};

const confidenceMeta: Record<ImportMatchConfidence, ConfidenceMeta> = {
	none: {
		label: 'No match',
		hint: 'Nothing matched this directory - pick the media yourself.',
		badgeClass: 'border-destructive/40 bg-destructive/10 text-destructive',
		rowClass: 'border-l-4 border-l-destructive bg-destructive/5',
		needsAttention: true,
		rank: 0
	},
	best_guess: {
		label: 'Best guess',
		hint: 'The title matched but the year did not, or an id resolved to a different title.',
		badgeClass: 'border-amber-500/40 bg-amber-500/15 text-amber-700 dark:text-amber-300',
		rowClass: 'border-l-4 border-l-amber-500 bg-amber-500/5',
		needsAttention: true,
		rank: 1
	},
	confident: {
		label: 'Confident',
		hint: 'The title and the year both match.',
		badgeClass: 'border-transparent bg-transparent text-muted-foreground',
		rowClass: 'border-l-4 border-l-transparent',
		needsAttention: false,
		rank: 2
	},
	exact_id: {
		label: 'Exact id',
		hint: 'This match was found from the ID in the directory name.',
		badgeClass: 'border-transparent bg-transparent text-muted-foreground',
		rowClass: 'border-l-4 border-l-transparent',
		needsAttention: false,
		rank: 3
	}
};

export function getConfidenceMeta(confidence: ImportMatchConfidence): ConfidenceMeta {
	return confidenceMeta[confidence];
}
