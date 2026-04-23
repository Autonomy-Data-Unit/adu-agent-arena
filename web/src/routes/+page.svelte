<script lang="ts">
	import { marked } from 'marked';
	import type { Leaderboard, Aggregate, Run, ScoreDetail } from '$lib/types';

	let { data: pageData } = $props();
	let data: Leaderboard = $state(pageData.leaderboard);
	let selectedAgent: string | null = $state(null);
	let expandedTest: string | null = $state(null);
	let selectedDetail: { run: Run; scorer: string; detail: ScoreDetail } | null = $state(null);
	let selectedTestDesc: string | null = $state(null);
	let sortColumn: string = $state('avg');
	let sortDirection: 'asc' | 'desc' = $state('desc');

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

	function getAgentTestScore(agent: string, test: string): number | null {
		const runs = data.runs.filter(r => r.agent === agent && r.test === test);
		const scores = runs.map(r => getRunOverallScore(r)).filter((s): s is number => s !== null);
		return scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : null;
	}

	function getOverallScore(agent: string): number | null {
		if (!data) return null;
		let total = 0;
		let count = 0;
		for (const test of data.tests) {
			const score = getAgentTestScore(agent, test);
			if (score !== null) {
				total += score;
				count++;
			}
		}
		return count > 0 ? total / count : null;
	}

	function getAgentSortValue(agent: string, column: string): number {
		if (column === 'avg') return getOverallScore(agent) ?? -Infinity;
		if (column === 'agent') return 0; // handled separately as string sort

		const aggs = aggLookup.get(agent);
		if (!aggs) return -Infinity;

		if (column === 'cost') return getAgentTotalCost(aggs) ?? -Infinity;
		if (column === 'time') return getAgentTotalTime(aggs) ?? -Infinity;
		if (column === 'runs') return getAgentRunCount(aggs);

		// Test column — compute from runs
		return getAgentTestScore(agent, column) ?? -Infinity;
	}

	function toggleSort(column: string) {
		if (sortColumn === column) {
			sortDirection = sortDirection === 'desc' ? 'asc' : 'desc';
		} else {
			sortColumn = column;
			sortDirection = column === 'agent' ? 'asc' : 'desc';
		}
	}

	function sortIndicator(column: string): string {
		if (sortColumn !== column) return '';
		return sortDirection === 'desc' ? ' \u25BC' : ' \u25B2';
	}

	let sortedAgents = $derived(
		data
			? [...data.agents].sort((a, b) => {
					let cmp: number;
					if (sortColumn === 'agent') {
						cmp = a.localeCompare(b);
					} else {
						cmp = getAgentSortValue(a, sortColumn) - getAgentSortValue(b, sortColumn);
					}
					return sortDirection === 'desc' ? -cmp : cmp;
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

	function getAgentRuns(agent: string, test?: string): Run[] {
		if (!data) return [];
		return data.runs
			.filter((r) => r.agent === agent && (!test || r.test === test))
			.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
	}

	interface TestSummary {
		test: string;
		runs: Run[];
		avgScore: number | null;
		avgCost: number | null;
		avgTime: number | null;
	}

	function getAgentTestSummaries(agent: string): TestSummary[] {
		if (!data) return [];
		const summaries: TestSummary[] = [];
		for (const test of data.tests) {
			const runs = getAgentRuns(agent, test);
			if (runs.length === 0) continue;

			const scores = runs.map(r => getRunOverallScore(r)).filter((s): s is number => s !== null);
			const costs = runs.map(r => r.total_cost).filter((c): c is number => c !== undefined && c !== null);
			const times = runs.map(r => r.total_time).filter((t): t is number => t !== undefined && t !== null);

			summaries.push({
				test,
				runs,
				avgScore: scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : null,
				avgCost: costs.length > 0 ? costs.reduce((a, b) => a + b, 0) / costs.length : null,
				avgTime: times.length > 0 ? times.reduce((a, b) => a + b, 0) / times.length : null,
			});
		}
		return summaries;
	}

	let agentTestSummaries = $derived(selectedAgent ? getAgentTestSummaries(selectedAgent) : []);

	function scoreColor(val: number): string {
		if (val >= 0.9) return '#3fb950';
		if (val >= 0.5) return '#d29922';
		return '#f85149';
	}

	function getRunOverallScore(run: Run): number | null {
		const details = run.score_details || {};
		let total = 0;
		let count = 0;
		for (const detail of Object.values(details)) {
			if (typeof detail.value === 'object' && detail.value !== null) {
				const vals = detail.value as Record<string, number>;
				if ('overall' in vals) { total += vals.overall; count++; }
			}
		}
		return count > 0 ? total / count : null;
	}

	function getScorersForRun(run: Run): { name: string; type: 'deterministic' | 'judge'; scores: Record<string, number | string>; detail: ScoreDetail }[] {
		const scorers: { name: string; type: 'deterministic' | 'judge'; scores: Record<string, number | string>; detail: ScoreDetail }[] = [];
		const details = run.score_details || {};

		for (const [scorerName, detail] of Object.entries(details)) {
			const isJudge = scorerName.includes('judge');
			const relevantScores: Record<string, number | string> = {};

			if (typeof detail.value === 'object' && detail.value !== null) {
				for (const [k, v] of Object.entries(detail.value as Record<string, number>)) {
					relevantScores[k] = v;
				}
			}

			scorers.push({
				name: scorerName,
				type: isJudge ? 'judge' : 'deterministic',
				scores: relevantScores,
				detail,
			});
		}

		return scorers;
	}

	function openDetail(run: Run, scorerName: string, detail: ScoreDetail) {
		selectedDetail = { run, scorer: scorerName, detail };
	}

	function closeDetail() {
		selectedDetail = null;
	}

	function formatDetailValue(val: string | number | Record<string, number>): string {
		if (typeof val === 'object') {
			return Object.entries(val).map(([k, v]) => `${k}: ${typeof v === 'number' ? (v * 100).toFixed(1) + '%' : v}`).join(', ');
		}
		if (typeof val === 'number') return (val * 100).toFixed(1) + '%';
		return String(val);
	}
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
						<th class="sortable" onclick={() => toggleSort('agent')}>Agent{sortIndicator('agent')}</th>
						{#each data.tests as test}
							<th class="sortable">
								<span onclick={() => toggleSort(test)}>{test}{sortIndicator(test)}</span>
								{#if data.test_descriptions?.[test]}
									<button class="info-btn" onclick={(e) => { e.stopPropagation(); selectedTestDesc = selectedTestDesc === test ? null : test; }} title="View test description">?</button>
								{/if}
							</th>
						{/each}
						<th class="sortable" onclick={() => toggleSort('avg')}>Avg{sortIndicator('avg')}</th>
						<th class="sortable" onclick={() => toggleSort('cost')}>Cost{sortIndicator('cost')}</th>
						<th class="sortable" onclick={() => toggleSort('time')}>Time{sortIndicator('time')}</th>
						<th class="sortable" onclick={() => toggleSort('runs')}>Runs{sortIndicator('runs')}</th>
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
								{@const testScore = getAgentTestScore(agent, test)}
								<td class="score" style:color={testScore !== null ? scoreColor(testScore) : undefined}>
									{formatScore(testScore)}
								</td>
							{/each}
							<td class="score avg" style:color={getOverallScore(agent) !== null ? scoreColor(getOverallScore(agent)!) : undefined}>
								{formatScore(getOverallScore(agent))}
							</td>
							<td class="cost">{formatCost(getAgentTotalCost(agentAggs))}</td>
							<td class="time">{formatTime(getAgentTotalTime(agentAggs))}</td>
							<td class="runs">{getAgentRunCount(agentAggs)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</section>

	{#if selectedAgent && agentTestSummaries.length > 0}
		<section class="detail">
			<h2>{selectedAgent}</h2>
			<div class="table-wrap">
				<table>
					<thead>
						<tr>
							<th>Test</th>
							<th>Avg Score</th>
							<th>Cost</th>
							<th>Time</th>
							<th>Runs</th>
						</tr>
					</thead>
					<tbody>
						{#each agentTestSummaries as summary}
							{@const latestSummary = summary.runs.find(r => r.summary)?.summary}
							<tr
								class="test-summary-row"
								class:expanded={expandedTest === summary.test}
								onclick={() => expandedTest = expandedTest === summary.test ? null : summary.test}
							>
								<td class="agent-name">{summary.test}</td>
								<td class="score avg" style:color={summary.avgScore !== null ? scoreColor(summary.avgScore) : undefined}>
									{summary.avgScore !== null ? formatScore(summary.avgScore) : '-'}
								</td>
								<td class="cost">{formatCost(summary.avgCost)}</td>
								<td class="time">{formatTime(summary.avgTime)}</td>
								<td class="runs">{summary.runs.length}</td>
							</tr>
							{#if latestSummary && expandedTest !== summary.test}
								<tr class="summary-row">
									<td colspan="5" class="summary-cell">{latestSummary}</td>
								</tr>
							{/if}
							{#if expandedTest === summary.test}
								{#each summary.runs as run}
									<tr class="run-detail-row">
										<td class="scores-cell" colspan="2">
											{#each getScorersForRun(run) as scorer}
												{#each Object.entries(scorer.scores) as [key, val]}
													<button
														class="score-tag"
														class:judge={scorer.type === 'judge'}
														class:clickable={!!scorer.detail}
														style:color={typeof val === 'number' ? scoreColor(val) : undefined}
														onclick={(e) => { e.stopPropagation(); if (scorer.detail) openDetail(run, scorer.name, scorer.detail); }}
													>
														<span class="score-type-label">{scorer.type === 'judge' ? 'J' : 'D'}</span>
														{key}: {typeof val === 'number' ? formatScore(val) : val}
													</button>
												{/each}
											{/each}
										</td>
										<td class="cost">{formatCost(run.total_cost)}</td>
										<td class="time">{formatTime(run.total_time)}</td>
										<td class="timestamp">{new Date(run.timestamp).toLocaleString()}</td>
									</tr>
									{#if run.summary}
										<tr class="summary-row">
											<td colspan="5" class="summary-cell">{run.summary}</td>
										</tr>
									{/if}
								{/each}
							{/if}
						{/each}
					</tbody>
				</table>
			</div>
		</section>
	{/if}
{/if}

{#if selectedDetail}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="panel-overlay" onclick={closeDetail} onkeydown={(e) => { if (e.key === 'Escape') closeDetail(); }}>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="panel" onclick={(e) => e.stopPropagation()}>
			<div class="panel-header">
				<h3>
					{#if selectedDetail.scorer.includes('judge')}
						<span class="badge judge">Judge</span>
					{:else}
						<span class="badge deterministic">Deterministic</span>
					{/if}
					{selectedDetail.scorer}
				</h3>
				<button class="panel-close" onclick={closeDetail}>x</button>
			</div>

			<div class="panel-meta">
				<span>{selectedDetail.run.test}</span>
				<span>{selectedDetail.run.agent}</span>
				<span>{new Date(selectedDetail.run.timestamp).toLocaleString()}</span>
			</div>

			{#if typeof selectedDetail.detail.value === 'object' && selectedDetail.detail.value !== null}
				<div class="panel-section">
					<h4>Checks</h4>
					<div class="checks-grid">
						{#each Object.entries(selectedDetail.detail.value as Record<string, number>) as [check, val]}
							<div class="check-row">
								<span class="check-name">{check}</span>
								<span class="check-val" class:pass={val >= 1} class:partial={val > 0 && val < 1} class:fail={val <= 0}>
									{(val * 100).toFixed(1)}%
								</span>
							</div>
						{/each}
					</div>
				</div>
			{:else}
				<div class="panel-section">
					<h4>Result</h4>
					<p class="panel-value">{formatDetailValue(selectedDetail.detail.value)}</p>
				</div>
			{/if}

			{#if selectedDetail.detail.explanation}
				<div class="panel-section">
					<h4>Explanation</h4>
					{#if selectedDetail.scorer.includes('judge')}
						<div class="panel-explanation markdown">
							{@html marked(selectedDetail.detail.explanation)}
						</div>
					{:else}
						<div class="panel-explanation">
							{#each selectedDetail.detail.explanation.split('; ') as line}
								<p class="det-line">{line}</p>
							{/each}
						</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>
{/if}

{#if selectedTestDesc && data.test_descriptions?.[selectedTestDesc]}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="panel-overlay" onclick={() => selectedTestDesc = null} onkeydown={(e) => { if (e.key === 'Escape') selectedTestDesc = null; }}>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="panel" onclick={(e) => e.stopPropagation()}>
			<div class="panel-header">
				<h3>{selectedTestDesc}</h3>
				<button class="panel-close" onclick={() => selectedTestDesc = null}>x</button>
			</div>
			<div class="panel-explanation markdown">
				{@html marked(data.test_descriptions[selectedTestDesc])}
			</div>
		</div>
	</div>
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

	th.sortable {
		cursor: pointer;
		user-select: none;
	}

	th.sortable:hover {
		color: #e6edf3;
	}

	th.sortable span {
		cursor: pointer;
	}

	.info-btn {
		background: none;
		border: 1px solid #30363d;
		color: #8b949e;
		font-size: 0.625rem;
		font-weight: 700;
		width: 1.125rem;
		height: 1.125rem;
		border-radius: 50%;
		cursor: pointer;
		margin-left: 0.25rem;
		padding: 0;
		vertical-align: middle;
		line-height: 1;
	}

	.info-btn:hover {
		color: #e6edf3;
		border-color: #58a6ff;
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
		gap: 0.375rem;
		flex-wrap: wrap;
	}

	.score-tag {
		background: #21262d;
		padding: 0.125rem 0.5rem;
		border-radius: 3px;
		font-size: 0.75rem;
		white-space: nowrap;
		border-left: 2px solid #3fb950;
		border-top: none;
		border-right: none;
		border-bottom: none;
		color: #c9d1d9;
		font-family: inherit;
		display: inline-flex;
		align-items: center;
		gap: 0.375rem;
	}

	.score-tag.judge {
		border-left-color: #d29922;
	}

	.score-tag.clickable {
		cursor: pointer;
	}

	.score-tag.clickable:hover {
		background: #30363d;
	}

	.score-type-label {
		font-size: 0.625rem;
		font-weight: 700;
		opacity: 0.5;
	}

	.timestamp {
		color: #8b949e;
		white-space: nowrap;
	}

	.test-summary-row {
		cursor: pointer;
	}

	.test-summary-row.expanded {
		background: #1c2128;
		border-bottom-color: transparent;
	}

	.run-detail-row {
		background: #161b22;
	}

	.run-detail-row:hover {
		background: #1c2128;
	}

	.summary-row {
		background: #161b22;
	}

	.summary-row:hover {
		background: #161b22;
		cursor: default;
	}

	.summary-cell {
		padding: 0.25rem 0.75rem 0.75rem;
		font-size: 0.8125rem;
		color: #8b949e;
		font-style: italic;
		line-height: 1.5;
		border-bottom: 1px solid #21262d;
	}

	section h2 {
		font-size: 1.125rem;
		color: #e6edf3;
		margin: 0 0 0.5rem;
	}

	/* Panel overlay */
	.panel-overlay {
		position: fixed;
		top: 0;
		right: 0;
		bottom: 0;
		left: 0;
		background: rgba(0, 0, 0, 0.5);
		z-index: 100;
		display: flex;
		justify-content: flex-end;
	}

	.panel {
		width: min(600px, 90vw);
		background: #161b22;
		border-left: 1px solid #30363d;
		padding: 1.5rem;
		overflow-y: auto;
		animation: slide-in 0.15s ease-out;
	}

	@keyframes slide-in {
		from {
			transform: translateX(100%);
		}
		to {
			transform: translateX(0);
		}
	}

	.panel-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
		padding-bottom: 0.75rem;
		border-bottom: 1px solid #30363d;
	}

	.panel-header h3 {
		margin: 0;
		font-size: 1rem;
		color: #e6edf3;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.panel-close {
		background: none;
		border: 1px solid #30363d;
		color: #8b949e;
		font-size: 1rem;
		cursor: pointer;
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
	}

	.panel-close:hover {
		color: #e6edf3;
		background: #21262d;
	}

	.badge {
		font-size: 0.625rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		padding: 0.125rem 0.375rem;
		border-radius: 3px;
	}

	.badge.deterministic {
		background: rgba(63, 185, 80, 0.15);
		color: #3fb950;
	}

	.badge.judge {
		background: rgba(210, 153, 34, 0.15);
		color: #d29922;
	}

	.panel-meta {
		display: flex;
		gap: 1rem;
		font-size: 0.75rem;
		color: #8b949e;
		margin-bottom: 1.5rem;
	}

	.panel-section {
		margin-bottom: 1.5rem;
	}

	.panel-section h4 {
		margin: 0 0 0.5rem;
		font-size: 0.75rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: #8b949e;
	}

	.panel-value {
		margin: 0;
		font-size: 1.125rem;
		color: #e6edf3;
		font-weight: 600;
	}

	.checks-grid {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
	}

	.check-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.375rem 0.75rem;
		background: #0d1117;
		border-radius: 4px;
		border: 1px solid #21262d;
	}

	.check-name {
		font-size: 0.8125rem;
		color: #c9d1d9;
	}

	.check-val {
		font-size: 0.8125rem;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}

	.check-val.pass {
		color: #3fb950;
	}

	.check-val.partial {
		color: #d29922;
	}

	.check-val.fail {
		color: #f85149;
	}

	.det-line {
		margin: 0.25rem 0;
		font-size: 0.8125rem;
		color: #c9d1d9;
	}

	.panel-explanation {
		font-size: 0.8125rem;
		line-height: 1.6;
		color: #c9d1d9;
		background: #0d1117;
		padding: 1rem;
		border-radius: 6px;
		border: 1px solid #21262d;
		max-height: 60vh;
		overflow-y: auto;
	}

	.panel-explanation:not(.markdown) {
		white-space: pre-wrap;
	}

	.panel-explanation.markdown :global(h1),
	.panel-explanation.markdown :global(h2),
	.panel-explanation.markdown :global(h3),
	.panel-explanation.markdown :global(h4) {
		color: #e6edf3;
		margin: 1rem 0 0.5rem;
		font-size: 0.875rem;
	}

	.panel-explanation.markdown :global(strong) {
		color: #e6edf3;
	}

	.panel-explanation.markdown :global(ol),
	.panel-explanation.markdown :global(ul) {
		padding-left: 1.5rem;
		margin: 0.5rem 0;
	}

	.panel-explanation.markdown :global(li) {
		margin: 0.25rem 0;
	}

	.panel-explanation.markdown :global(p) {
		margin: 0.5rem 0;
	}
</style>
