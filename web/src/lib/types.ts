export interface ScoreDetail {
	value: string | number | Record<string, number>;
	explanation: string;
}

export interface Run {
	id: string;
	agent: string;
	test: string;
	timestamp: string;
	status: string;
	scores: Record<string, number | string>;
	score_details: Record<string, ScoreDetail>;
	total_time?: number;
	total_cost?: number;
	input_tokens?: number;
	output_tokens?: number;
}

export interface Aggregate {
	agent: string;
	test: string;
	run_count: number;
	[key: string]: string | number;
}

export interface Leaderboard {
	generated_at: string;
	agents: string[];
	tests: string[];
	runs: Run[];
	aggregates: Aggregate[];
}
