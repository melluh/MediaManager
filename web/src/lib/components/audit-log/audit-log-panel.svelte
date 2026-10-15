<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import EmptyState from '$lib/components/empty-state.svelte';
	import PageLoading from '$lib/components/page-loading.svelte';
	import * as Pagination from '$lib/components/ui/pagination/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { AUDIT_LOG_PAGE_SIZE, type AuditLogFilters } from '$lib/api/audit-log';
	import type { AuditLogPage } from '$lib/api/api';
	import History from '@lucide/svelte/icons/history';
	import Layers from '@lucide/svelte/icons/layers';
	import type { Snippet } from 'svelte';
	import { auditCategories } from './audit-actions';
	import AuditLogTable from './audit-log-table.svelte';

	let {
		log,
		filters,
		showUser = true,
		extraFilters
	}: {
		log: Promise<AuditLogPage | null>;
		filters: AuditLogFilters;
		showUser?: boolean;
		/** More filter controls, next to the category filter. */
		extraFilters?: Snippet<[SetParams]>;
	} = $props();

	type SetParams = (params: Record<string, string | null>) => void;

	/** Navigates to the same page with some search params changed; null removes one. */
	const setParams: SetParams = (params) => {
		const url = new URL(page.url);
		for (const [key, value] of Object.entries(params)) {
			if (value === null) url.searchParams.delete(key);
			else url.searchParams.set(key, value);
		}
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- the current (already resolved) URL with its query string changed
		goto(url, { keepFocus: true, noScroll: true });
	};

	const ALL = 'all';
</script>

<div class="flex flex-col gap-3">
	<div class="flex flex-wrap items-center gap-2">
		<Select.Root
			type="single"
			value={filters.category ?? ALL}
			onValueChange={(value) => setParams({ category: value === ALL ? null : value, page: null })}
		>
			<Select.Trigger class="w-48">
				{@const selected = filters.category ? auditCategories[filters.category] : null}
				{@const Icon = selected?.icon ?? Layers}
				<div class="flex min-w-0 items-center gap-2">
					<Icon class="size-4 shrink-0 text-muted-foreground" />
					<span class="truncate">{selected?.label ?? 'All activity'}</span>
				</div>
			</Select.Trigger>
			<Select.Content>
				<Select.Item value={ALL} label="All activity">
					<span class="flex items-center gap-2">
						<Layers class="size-4 shrink-0 text-muted-foreground" />
						All activity
					</span>
				</Select.Item>
				{#each Object.entries(auditCategories) as [value, { label, icon: Icon }] (value)}
					<Select.Item {value} {label}>
						<span class="flex items-center gap-2">
							<Icon class="size-4 shrink-0 text-muted-foreground" />
							{label}
						</span>
					</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
		{@render extraFilters?.(setParams)}
	</div>

	{#await log}
		<PageLoading message="Loading activity…" />
	{:then log}
		{#if !log}
			<p class="text-sm text-muted-foreground">Could not load activity.</p>
		{:else if log.items.length === 0}
			<EmptyState icon={History} title="No activity yet">
				Actions will show up here as they happen.
			</EmptyState>
		{:else}
			<AuditLogTable entries={log.items} {showUser} />
			{#if log.total > AUDIT_LOG_PAGE_SIZE}
				<Pagination.Root
					count={log.total}
					perPage={AUDIT_LOG_PAGE_SIZE}
					page={filters.page}
					onPageChange={(p) => setParams({ page: p === 1 ? null : String(p) })}
				>
					{#snippet children({ pages, currentPage })}
						<Pagination.Content>
							<Pagination.Item>
								<Pagination.PrevButton />
							</Pagination.Item>
							{#each pages as p (p.key)}
								{#if p.type === 'ellipsis'}
									<Pagination.Item>
										<Pagination.Ellipsis />
									</Pagination.Item>
								{:else}
									<Pagination.Item>
										<Pagination.Link page={p} isActive={currentPage === p.value}>
											{p.value}
										</Pagination.Link>
									</Pagination.Item>
								{/if}
							{/each}
							<Pagination.Item>
								<Pagination.NextButton />
							</Pagination.Item>
						</Pagination.Content>
					{/snippet}
				</Pagination.Root>
			{/if}
		{/if}
	{/await}
</div>
