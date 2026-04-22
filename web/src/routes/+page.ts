import type { Leaderboard } from '$lib/types';

export async function load({ fetch }) {
	const res = await fetch('/leaderboard.json');
	const data: Leaderboard = await res.json();
	return { leaderboard: data };
}
