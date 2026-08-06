import type { LayoutLoad } from './$types';
import { error } from '@sveltejs/kit';
import client from '$lib/api';

export const load: LayoutLoad = async ({ fetch }) => {
	const { data, response } = await client.GET('/api/v1/auth/metadata', { fetch: fetch });
	if (!response.ok) {
		throw error(503);
	}
	return { loginData: data };
};
