<script lang="ts">
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();
</script>

<svelte:head>
	<title>ADU Agent Arena</title>
	<meta name="description" content="Benchmarking coding agents on ADU data-led research tasks" />
</svelte:head>

<div class="app">
	<header>
		<h1>ADU Agent Arena</h1>
		<p class="subtitle">Benchmarking coding agents on data-led research tasks</p>
	</header>

	<main>
		{@render children()}
	</main>
</div>

<style>
	:global(body) {
		margin: 0;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
		background: #0d1117;
		color: #c9d1d9;
	}

	.app {
		max-width: 1200px;
		margin: 0 auto;
		padding: 2rem;
	}

	header {
		margin-bottom: 2rem;
		border-bottom: 1px solid #30363d;
		padding-bottom: 1rem;
	}

	header h1 {
		margin: 0;
		color: #e6edf3;
		font-size: 1.5rem;
	}

	.subtitle {
		margin: 0.25rem 0 0;
		color: #8b949e;
		font-size: 0.875rem;
	}
</style>
