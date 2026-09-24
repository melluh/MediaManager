<script lang="ts">
	import * as Select from '$lib/components/ui/select/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { Button, buttonVariants } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import ArrowUpDown from '@lucide/svelte/icons/arrow-up-down';
	import ListFilter from '@lucide/svelte/icons/list-filter';
	import HardDrive from '@lucide/svelte/icons/hard-drive';
	import Gauge from '@lucide/svelte/icons/gauge';
	import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
	import Captions from '@lucide/svelte/icons/captions';
	import { NO_SUBTITLES_KEY, qualityMap, subtitleLanguageKey } from '$lib/utils';
	import type { MovieListItem, Quality, ShowSummary, SubtitleLanguage } from '$lib/api/api';
	import type { DownloadedFilter, MediaSortOption } from '$lib/utils';

	let {
		items,
		isShow,
		sortBy = $bindable(),
		selectedGenres = $bindable(),
		downloadedFilter = $bindable(),
		selectedQualities = $bindable(),
		selectedSubtitles = $bindable()
	}: {
		items: (MovieListItem | ShowSummary)[];
		isShow: boolean;
		sortBy: MediaSortOption;
		selectedGenres: string[];
		downloadedFilter: DownloadedFilter;
		selectedQualities: Quality[];
		selectedSubtitles: string[];
	} = $props();

	const sortOptions: { value: MediaSortOption; label: string }[] = [
		{ value: 'newest', label: 'Newest first' },
		{ value: 'oldest', label: 'Oldest first' },
		{ value: 'alphabetical', label: 'Alphabetical' }
	];
	let sortLabel = $derived(sortOptions.find((o) => o.value === sortBy)?.label ?? 'Sort by');

	const downloadedOptions: { value: DownloadedFilter; label: string }[] = [
		{ value: 'all', label: 'All' },
		{ value: 'yes', label: 'Downloaded' },
		{ value: 'no', label: 'Not downloaded' }
	];
	let downloadedLabel = $derived(
		downloadedOptions.find((o) => o.value === downloadedFilter)?.label
	);

	let availableGenres = $derived(
		[...new Set(items.flatMap((item) => item.genres ?? []))].sort((a, b) => a.localeCompare(b))
	);
	let availableQualities = $derived(
		[
			...new Set(
				items
					.map((item) => ('quality' in item ? item.quality : null))
					.filter((quality): quality is Quality => quality != null)
			)
		].sort((a, b) => a - b)
	);

	// Languages found across the library, keyed like the filter itself so
	// regional variants get their own checkbox. Unknown is listed last.
	let availableSubtitleLanguages = $derived.by(() => {
		const byKey: Record<string, SubtitleLanguage> = {};
		for (const item of items) {
			if (!('subtitle_languages' in item)) continue;
			for (const language of item.subtitle_languages ?? []) {
				byKey[subtitleLanguageKey(language)] = language;
			}
		}
		return Object.entries(byKey).sort(([, a], [, b]) => {
			if ((a.code === 'und') !== (b.code === 'und')) return a.code === 'und' ? 1 : -1;
			return a.name.localeCompare(b.name);
		});
	});
	// Only offered once the backend's subtitle scan has reported on at least
	// one movie - before that, every option would match nothing.
	let hasSubtitleData = $derived(
		items.some((item) => 'subtitle_languages' in item && item.subtitle_languages != null)
	);

	function toggleSubtitle(key: string) {
		selectedSubtitles = selectedSubtitles.includes(key)
			? selectedSubtitles.filter((k) => k !== key)
			: [...selectedSubtitles, key];
	}

	function toggleGenre(genre: string) {
		selectedGenres = selectedGenres.includes(genre)
			? selectedGenres.filter((g) => g !== genre)
			: [...selectedGenres, genre];
	}

	function toggleQuality(quality: Quality) {
		selectedQualities = selectedQualities.includes(quality)
			? selectedQualities.filter((q) => q !== quality)
			: [...selectedQualities, quality];
	}

	let hasActiveFilters = $derived(
		selectedGenres.length > 0 ||
			downloadedFilter !== 'all' ||
			selectedQualities.length > 0 ||
			selectedSubtitles.length > 0
	);

	function resetFilters() {
		selectedGenres = [];
		downloadedFilter = 'all';
		selectedQualities = [];
		selectedSubtitles = [];
	}
</script>

<div class="flex flex-wrap items-center gap-2">
	<Select.Root type="single" bind:value={sortBy}>
		<Select.Trigger class="w-auto min-w-40 gap-2">
			<ArrowUpDown class="size-4 text-muted-foreground" />
			{sortLabel}
		</Select.Trigger>
		<Select.Content>
			<Select.Group>
				{#each sortOptions as option (option.value)}
					<Select.Item value={option.value} label={option.label}>{option.label}</Select.Item>
				{/each}
			</Select.Group>
		</Select.Content>
	</Select.Root>

	{#if availableGenres.length > 0}
		<DropdownMenu.Root>
			<DropdownMenu.Trigger class={buttonVariants({ variant: 'outline' })}>
				<ListFilter class="size-4 text-muted-foreground" />
				Genre
				{#if selectedGenres.length > 0}
					<Badge variant="secondary" class="ml-1">{selectedGenres.length}</Badge>
				{/if}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="start" class="max-h-80 overflow-y-auto">
				{#each availableGenres as genre (genre)}
					<DropdownMenu.CheckboxItem
						checked={selectedGenres.includes(genre)}
						closeOnSelect={false}
						onCheckedChange={() => toggleGenre(genre)}
					>
						{genre}
					</DropdownMenu.CheckboxItem>
				{/each}
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	{/if}

	{#if !isShow}
		<DropdownMenu.Root>
			<DropdownMenu.Trigger class={buttonVariants({ variant: 'outline' })}>
				<HardDrive class="size-4 text-muted-foreground" />
				Status
				{#if downloadedFilter !== 'all'}
					<Badge variant="secondary" class="ml-1">{downloadedLabel}</Badge>
				{/if}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="start">
				<DropdownMenu.RadioGroup bind:value={downloadedFilter}>
					{#each downloadedOptions as option (option.value)}
						<DropdownMenu.RadioItem value={option.value}>{option.label}</DropdownMenu.RadioItem>
					{/each}
				</DropdownMenu.RadioGroup>
			</DropdownMenu.Content>
		</DropdownMenu.Root>

		{#if availableQualities.length > 0}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger class={buttonVariants({ variant: 'outline' })}>
					<Gauge class="size-4 text-muted-foreground" />
					Quality
					{#if selectedQualities.length > 0}
						<Badge variant="secondary" class="ml-1">{selectedQualities.length}</Badge>
					{/if}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="start">
					{#each availableQualities as quality (quality)}
						<DropdownMenu.CheckboxItem
							checked={selectedQualities.includes(quality)}
							closeOnSelect={false}
							onCheckedChange={() => toggleQuality(quality)}
						>
							{qualityMap[quality]}
						</DropdownMenu.CheckboxItem>
					{/each}
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		{/if}

		{#if hasSubtitleData}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger class={buttonVariants({ variant: 'outline' })}>
					<Captions class="size-4 text-muted-foreground" />
					Subtitles
					{#if selectedSubtitles.length > 0}
						<Badge variant="secondary" class="ml-1">{selectedSubtitles.length}</Badge>
					{/if}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="start" class="max-h-80 overflow-y-auto">
					<DropdownMenu.CheckboxItem
						checked={selectedSubtitles.includes(NO_SUBTITLES_KEY)}
						closeOnSelect={false}
						onCheckedChange={() => toggleSubtitle(NO_SUBTITLES_KEY)}
					>
						None
					</DropdownMenu.CheckboxItem>
					{#if availableSubtitleLanguages.length > 0}
						<DropdownMenu.Separator />
					{/if}
					{#each availableSubtitleLanguages as [key, language] (key)}
						<DropdownMenu.CheckboxItem
							checked={selectedSubtitles.includes(key)}
							closeOnSelect={false}
							onCheckedChange={() => toggleSubtitle(key)}
						>
							{language.name}
						</DropdownMenu.CheckboxItem>
					{/each}
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		{/if}
	{/if}

	{#if hasActiveFilters}
		<Button variant="ghost" size="sm" onclick={resetFilters}>
			<RotateCcw class="size-4" />
			Reset filters
		</Button>
	{/if}
</div>
