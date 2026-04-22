<script lang="ts">
	import type { Leaderboard, Aggregate, Run } from '$lib/types';

	let { data: pageData } = $props();
	let data: Leaderboard = $state(pageData.leaderboard);
	let selectedAgent: string | null = $state(null);

	let hasData = $derived(data.runs.length > 0);

	function getAggregateLookup(aggregates: Aggregate[]): Map<string, Map<string, Aggregate>> {
		const lookup = new Map<string, Map<string, Aggregate>>();
		for (const agg of aggregates) {
			if (!lookup.has(agg.agent)) lookup.set(agg.agent, new Map());
			lookup.get(agg.agent)!.set(agg.test, agg);
		}
		return lookup;
	}

	let aggLookup = $derived(data ? getAggregateLookup(data.aggregates) : new Map());

	function getScoreKeys(aggregates: Aggregate[]): string[] {
		const keys = new Set<string>();
		for (const agg of aggregates) {
			for (const key of Object.keys(agg)) {
				if (key.endsWith('_mean') && key.startsWith('score_')) {
					keys.add(key.replace('_mean', '').replace('score_', ''));
				}
			}
		}
		return [...keys].sort();
	}

	let scoreKeys = $derived(data ? getScoreKeys(data.aggregates) : []);

	function getOverallScore(agentAggs: Map<string, Aggregate> | undefined): number | null {
		if (!agentAggs) return null;
		let total = 0;
		let count = 0;
		for (const agg of agentAggs.values()) {
			const overall = agg['score_overall_mean_mean'];
			if (typeof overall === 'number') {
				total += overall;
				count++;
			}
		}
		return count > 0 ? total / count : null;
	}

	let sortedAgents = $derived(
		data
			? [...data.agents].sort((a, b) => {
					const scoreA = getOverallScore(aggLookup.get(a)) ?? -1;
					const scoreB = getOverallScore(aggLookup.get(b)) ?? -1;
					return scoreB - scoreA;
				})
			: []
	);

	function formatScore(val: unknown): string {
		if (typeof val === 'number') return (val * 100).toFixed(1) + '%';
		return '-';
	}

	function formatCost(val: unknown): string {
		if (typeof val === 'number') return '$' + val.toFixed(2);
		return '-';
	}

	function formatTime(val: unknown): string {
		if (typeof val === 'number') return val.toFixed(0) + 's';
		return '-';
	}

	function getAgentTotalCost(agentAggs: Map<string, Aggregate> | undefined): number | null {
		if (!agentAggs) return null;
		let total = 0;
		let count = 0;
		for (const agg of agentAggs.values()) {
			const cost = agg['total_cost_mean'];
			if (typeof cost === 'number') {
				total += cost;
				count++;
			}
		}
		return count > 0 ? total : null;
	}

	function getAgentTotalTime(agentAggs: Map<string, Aggregate> | undefined): number | null {
		if (!agentAggs) return null;
		let total = 0;
		let count = 0;
		for (const agg of agentAggs.values()) {
			const time = agg['total_time_mean'];
			if (typeof time === 'number') {
				total += time;
				count++;
			}
		}
		return count > 0 ? total : null;
	}

	function getAgentRunCount(agentAggs: Map<string, Aggregate> | undefined): number {
		if (!agentAggs) return 0;
		let total = 0;
		for (const agg of agentAggs.values()) {
			total += agg.run_count;
		}
		return total;
	}

	function getAgentRuns(agent: string): Run[] {
		if (!data) return [];
		return data.runs
			.filter((r) => r.agent === agent)
			.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
	}

	let selectedRuns = $derived(selectedAgent ? getAgentRuns(selectedAgent) : []);
</script>

{#if !hasData}
	<div class="empty">
		<h2>No runs yet</h2>
		<p>Run an evaluation to see results here:</p>
		<pre>inspect eval src/adu_arena/tasks/medrxiv_scraper.py --model openai/gpt-4o</pre>
		<p>Then export the leaderboard:</p>
		<pre>python scripts/export_leaderboard.py</pre>
	</div>
{:else}
	<section>
		<h2>Leaderboard</h2>
		<p class="meta">
			{data.agents.length} agent{data.agents.length !== 1 ? 's' : ''} &middot;
			{data.tests.length} test{data.tests.length !== 1 ? 's' : ''} &middot;
			{data.runs.length} run{data.runs.length !== 1 ? 's' : ''} &middot;
			Updated {new Date(data.generated_at).toLocaleDateString()}
		</p>

		<div class="table-wrap">
			<table>
				<thead>
					<tr>
						<th>Agent</th>
						{#each data.tests as test}
							<th>{test}</th>
						{/each}
						<th>Avg</th>
						<th>Cost</th>
						<th>Time</th>
						<th>Runs</th>
					</tr>
				</thead>
				<tbody>
					{#each sortedAgents as agent}
						{@const agentAggs = aggLookup.get(agent)}
						<tr
							class:selected={selectedAgent === agent}
							onclick={() => (selectedAgent = selectedAgent === agent ? null : agent)}
						>
							<td class="agent-name">{agent}</td>
							{#each data.tests as test}
								{@const agg = agentAggs?.get(test)}
								<td class="score">
									{formatScore(agg?.['score_overall_mean_mean'])}
								</td>
							{/each}
							<td class="score avg">{formatScore(getOverallScore(agentAggs))}</td>
							<td class="cost">{formatCost(getAgentTotalCost(agentAggs))}</td>
							<td class="time">{formatTime(getAgentTotalTime(agentAggs))}</td>
							<td class="runs">{getAgentRunCount(agentAggs)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</section>

	{#if selectedAgent && selectedRuns.length > 0}
		<section class="detail">
			<h2>Runs for {selectedAgent}</h2>
			<div class="table-wrap">
				<table>
					<thead>
						<tr>
							<th>Test</th>
							<th>Time</th>
							<th>Status</th>
							<th>Scores</th>
							<th>Timestamp</th>
						</tr>
					</thead>
					<tbody>
						{#each selectedRuns as run}
							<tr>
								<td>{run.test}</td>
								<td class="time">{formatTime(run.total_time)}</td>
								<td class="status" class:pass={run.status === 'success'}
									>{run.status}</td
								>
								<td class="scores-cell">
									{#each Object.entries(run.scores) as [key, val]}
										<span class="score-tag"
											>{key.replace('score_', '')}: {formatScore(val)}</span
										>
									{/each}
								</td>
								<td class="timestamp"
									>{new Date(run.timestamp).toLocaleString()}</td
								>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</section>
	{/if}
{/if}

<style>
	.empty {
		text-align: center;
		padding: 3rem 1rem;
	}

	.empty pre {
		background: #161b22;
		padding: 0.75rem 1rem;
		border-radius: 6px;
		display: inline-block;
		text-align: left;
		font-size: 0.875rem;
	}

	.meta {
		color: #8b949e;
		font-size: 0.875rem;
		margin-bottom: 1rem;
	}

	.table-wrap {
		overflow-x: auto;
	}

	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.875rem;
	}

	th {
		text-align: left;
		padding: 0.5rem 0.75rem;
		border-bottom: 2px solid #30363d;
		color: #8b949e;
		font-weight: 600;
		white-space: nowrap;
	}

	td {
		padding: 0.5rem 0.75rem;
		border-bottom: 1px solid #21262d;
	}

	tr:hover {
		background: #161b22;
		cursor: pointer;
	}

	tr.selected {
		background: #1c2128;
	}

	.agent-name {
		font-weight: 600;
		color: #e6edf3;
		white-space: nowrap;
	}

	.score {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}

	.avg {
		font-weight: 600;
		color: #58a6ff;
	}

	.cost,
	.time,
	.runs {
		text-align: right;
		color: #8b949e;
		font-variant-numeric: tabular-nums;
	}

	.detail {
		margin-top: 2rem;
	}

	.status {
		color: #f85149;
	}

	.status.pass {
		color: #3fb950;
	}

	.scores-cell {
		display: flex;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.score-tag {
		background: #21262d;
		padding: 0.125rem 0.5rem;
		border-radius: 3px;
		font-size: 0.75rem;
		white-space: nowrap;
	}

	.timestamp {
		color: #8b949e;
		white-space: nowrap;
	}

	section h2 {
		font-size: 1.125rem;
		color: #e6edf3;
		margin: 0 0 0.5rem;
	}
</style>
