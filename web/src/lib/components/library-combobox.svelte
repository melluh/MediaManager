<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import FolderInput from '@lucide/svelte/icons/folder-input';
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import client from '$lib/api';
	import type { PublicShow, PublicMovie, LibraryItem } from '$lib/api/api';
	import { invalidateAll } from '$app/navigation';

	let {
		media,
		mediaType
	}: {
		media: PublicShow | PublicMovie;
		mediaType: 'tv' | 'movie';
	} = $props();

	let value = $derived(media.library === '' ? 'Default' : media.library);
	let libraries: LibraryItem[] = $state([]);

	onMount(async () => {
		const tvLibraries = await client.GET('/api/v1/tv/shows/libraries');
		const movieLibraries = await client.GET('/api/v1/movies/libraries');

		if (mediaType === 'tv') {
			libraries = tvLibraries.data as LibraryItem[];
		} else {
			libraries = movieLibraries.data as LibraryItem[];
		}

		libraries.push({
			name: 'Default',
			path: 'Default'
		} as LibraryItem);
	});

	async function handleSelect(libraryName: string) {
		let response;
		if (mediaType === 'tv') {
			response = await client.POST('/api/v1/tv/shows/{show_id}/library', {
				params: {
					path: { show_id: media.id! },
					query: { library: libraryName }
				}
			});
		} else {
			response = await client.POST('/api/v1/movies/{movie_id}/library', {
				params: {
					path: { movie_id: media.id! },
					query: { library: libraryName }
				}
			});
		}
		if (response.error) {
			toast.error('Failed to update library');
		} else {
			toast.success(`Library updated to ${libraryName}`);
			media.library = libraryName;
		}
		await invalidateAll();
	}
</script>

<DropdownMenu.Sub>
	<DropdownMenu.SubTrigger>
		<FolderInput />
		Move Library
	</DropdownMenu.SubTrigger>
	<DropdownMenu.SubContent>
		<DropdownMenu.RadioGroup {value} onValueChange={handleSelect}>
			{#each libraries as item (item.name)}
				<DropdownMenu.RadioItem value={item.name}>
					{item.name}
				</DropdownMenu.RadioItem>
			{/each}
		</DropdownMenu.RadioGroup>
	</DropdownMenu.SubContent>
</DropdownMenu.Sub>
