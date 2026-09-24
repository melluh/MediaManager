<script lang="ts">
	import { Badge } from '$lib/components/ui/badge/index.js';
	import Captions from '@lucide/svelte/icons/captions';
	import FileText from '@lucide/svelte/icons/file-text';
	import Package from '@lucide/svelte/icons/package';
	import type { SubtitleTrack } from '$lib/api/api';
	import { subtitleFormat } from '$lib/components/media-file-format';

	// Subtitle language/track fields ultimately come from a downloaded file's
	// own filename or embedded metadata - untrusted input. The backend already
	// sanitizes them, but they're still rendered as plain text interpolation
	// here (never `{@html}`) as defense in depth.
	let { subtitles }: { subtitles: SubtitleTrack[] } = $props();
</script>

<section class="flex flex-col gap-2">
	<h3 class="flex items-center gap-2 text-sm font-medium">
		<Captions class="size-4 text-muted-foreground" />
		Subtitles
		{#if subtitles.length > 0}
			<span class="text-xs font-normal text-muted-foreground">{subtitles.length}</span>
		{/if}
	</h3>
	{#if subtitles.length === 0}
		<p class="rounded-lg border border-dashed px-3 py-2 text-xs text-muted-foreground">
			No embedded subtitle tracks or subtitle files next to this file.
		</p>
	{:else}
		<!-- Listed in file order (embedded streams first, then sidecars), matching
		     the track order a player shows. -->
		<ul class="max-h-64 divide-y overflow-y-auto rounded-lg border bg-muted/40">
			{#each subtitles as subtitle, i (i)}
				{@const format = subtitleFormat(subtitle.codec)}
				<li class="flex items-center justify-between gap-3 px-3 py-2">
					<div class="flex min-w-0 flex-wrap items-center gap-1.5">
						<span
							class="truncate text-sm font-medium"
							class:text-muted-foreground={subtitle.language.code === 'und'}
						>
							{subtitle.language.name}
						</span>
						{#if subtitle.forced}
							<Badge variant="secondary">Forced</Badge>
						{/if}
						{#if subtitle.hearing_impaired}
							<Badge variant="secondary" title="Subtitles for the deaf and hard of hearing">
								SDH
							</Badge>
						{/if}
					</div>
					<div class="flex shrink-0 items-center gap-2 text-xs text-muted-foreground">
						{#if format}
							<span
								class="flex items-center gap-1"
								title={format.kind ? `${format.kind}-based subtitles` : undefined}
							>
								<Badge variant="outline" class="font-mono">{format.label}</Badge>
								{#if format.kind}{format.kind}{/if}
							</span>
						{/if}
						{#if subtitle.source === 'embedded'}
							<span class="flex items-center gap-1" title="Stored inside the video file">
								<Package class="size-3" />
								Embedded
							</span>
						{:else}
							<span
								class="flex items-center gap-1"
								title="Separate subtitle file next to the video"
							>
								<FileText class="size-3" />
								External
							</span>
						{/if}
					</div>
				</li>
			{/each}
		</ul>
	{/if}
</section>
