<script lang="ts">
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Progress } from '$lib/components/ui/progress/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import MediaImage from '$lib/components/media-image.svelte';
	import DownloadDetailsDialog from '$lib/components/downloads/download-details-dialog.svelte';
	import { getDownloadStatusBadge } from '$lib/components/downloads/download-status.js';
	import Film from '@lucide/svelte/icons/film';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import type { TorrentWithProgress } from '$lib/api/api';
	import { cn, formatAddedTime, formatBytes } from '$lib/utils';

	let { torrent }: { torrent: TorrentWithProgress } = $props();

	let detailsOpen = $state(false);
	let posterLoaded = $state(false);
	let backdropLoaded = $state(false);

	let displayName = $derived(torrent.media?.name ?? torrent.title);
	let sizeLabel = $derived(formatBytes(torrent.download_progress?.total_bytes));
	let addedLabel = $derived(formatAddedTime(torrent.initiated_at));
	let statusBadge = $derived(getDownloadStatusBadge(torrent));
</script>

<Dialog.Root bind:open={detailsOpen}>
	<Dialog.Trigger>
		{#snippet child({ props })}
			<div
				role="button"
				tabindex="0"
				class="group block w-full cursor-pointer text-left"
				{...props}
			>
				<Card.Root class="overflow-hidden py-0 transition-shadow group-hover:shadow-md">
					{#if torrent.download_progress}
						<Progress
							value={torrent.download_progress.progress}
							class={cn(
								'h-1 w-full rounded-none',
								torrent.download_progress.state === 'downloading' && 'animate-pulse'
							)}
						/>
					{/if}
					<div class="relative h-16 w-full overflow-hidden bg-muted">
						{#if torrent.media}
							<MediaImage
								media={torrent.media}
								variant="backdrop"
								className="h-full w-full object-cover"
								bind:loaded={backdropLoaded}
							/>
							{#if !backdropLoaded}
								<Skeleton class="absolute inset-0 h-full w-full" />
							{/if}
						{/if}
					</div>
					<div class="flex items-start gap-3 p-3">
						<div class="relative aspect-2/3 w-24 shrink-0 overflow-hidden rounded-md">
							{#if torrent.media}
								<MediaImage
									media={torrent.media}
									className="h-full w-full object-cover"
									bind:loaded={posterLoaded}
								/>
								{#if !posterLoaded}
									<Skeleton class="absolute inset-0 h-full w-full" />
								{/if}
							{:else}
								<div class="flex h-full w-full items-center justify-center bg-muted">
									<Film class="h-5 w-5 text-muted-foreground" />
								</div>
							{/if}
						</div>
						<div class="flex min-w-0 flex-1 flex-col justify-between gap-2 self-stretch">
							<div class="min-w-0 space-y-1">
								<p class="truncate text-sm font-medium" title={displayName}>{displayName}</p>
								{#if sizeLabel || torrent.indexer}
									<div class="flex min-w-0 items-center gap-1 text-xs text-muted-foreground">
										{#if sizeLabel}
											<span class="shrink-0">{sizeLabel}</span>
										{/if}
										{#if sizeLabel && torrent.indexer}
											<span class="shrink-0">&middot;</span>
										{/if}
										{#if torrent.indexer}
											{#if torrent.comments}
												<a
													href={torrent.comments}
													target="_blank"
													rel="noopener noreferrer external"
													class="min-w-0 truncate hover:text-foreground hover:underline"
													onclick={(event) => event.stopPropagation()}
												>
													{torrent.indexer}
												</a>
											{:else}
												<span class="min-w-0 truncate">{torrent.indexer}</span>
											{/if}
										{/if}
									</div>
								{/if}
							</div>
							<div class="space-y-1">
								{#if addedLabel}
									<p class="flex items-center gap-1.5 text-xs text-muted-foreground">
										<CalendarClock class="size-3.5" />
										{addedLabel}
									</p>
								{/if}
								<Badge variant={statusBadge.variant} class="w-fit shrink-0 self-start">
									<statusBadge.icon class="mr-1 size-3" />
									{statusBadge.label}
								</Badge>
							</div>
						</div>
					</div>
				</Card.Root>
			</div>
		{/snippet}
	</Dialog.Trigger>
	<DownloadDetailsDialog {torrent} />
</Dialog.Root>
