#!/usr/bin/env python3
"""Generate human-readable assessment summaries for each test run.

Reads existing leaderboard.json, finds runs without summaries, and asks
an LLM to write a 2-3 sentence assessment based on the scores and judge
reasoning. Writes summaries back into leaderboard.json.
"""

import json
import sys
from pathlib import Path

import anthropic

SUMMARY_PROMPT = """\
You are reviewing the results of a coding agent benchmark run. Write a concise 2-3 sentence assessment of how the agent performed on this task. Be specific about what went well and what didn't. Do not repeat the scores — focus on the narrative.

## Task
{test_name}

## Agent
{agent}

## Scores
{scores_text}

## Judge reasoning
{judge_reasoning}

## Deterministic check results
{det_results}

Write your assessment (2-3 sentences, no preamble):
"""


def generate_summaries(
    leaderboard_path: str = "web/static/leaderboard.json",
    model: str = "claude-sonnet-4-20250514",
) -> None:
    path = Path(leaderboard_path)
    if not path.exists():
        print(f"Leaderboard not found: {leaderboard_path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(path.read_text())
    client = anthropic.Anthropic()

    runs_needing_summary = [
        r for r in data["runs"]
        if r.get("status") == "success"
        and not r.get("summary")
        and r.get("score_details")
    ]

    if not runs_needing_summary:
        print("All runs already have summaries (or no score details).")
        return

    print(f"Generating summaries for {len(runs_needing_summary)} runs...")

    for i, run in enumerate(runs_needing_summary, 1):
        details = run.get("score_details", {})

        # Build scores text
        scores_parts = []
        for scorer_name, detail in details.items():
            if isinstance(detail["value"], dict):
                for k, v in detail["value"].items():
                    scores_parts.append(f"{scorer_name}.{k}: {v*100:.0f}%" if isinstance(v, float) else f"{scorer_name}.{k}: {v}")
            else:
                scores_parts.append(f"{scorer_name}: {detail['value']}")
        scores_text = "\n".join(scores_parts) if scores_parts else "No scores available"

        # Extract judge reasoning
        judge = details.get("judge_scorer", {})
        judge_reasoning = judge.get("explanation", "No judge reasoning available")

        # Extract deterministic results
        det = {}
        for name, detail in details.items():
            if "judge" not in name:
                det[name] = detail.get("explanation", "")
        det_results = "\n".join(f"{k}: {v}" for k, v in det.items()) if det else "No deterministic details"

        prompt = SUMMARY_PROMPT.format(
            test_name=run["test"],
            agent=run["agent"],
            scores_text=scores_text,
            judge_reasoning=judge_reasoning,
            det_results=det_results,
        )

        try:
            response = client.messages.create(
                model=model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            summary = response.content[0].text.strip()
            run["summary"] = summary
            print(f"  [{i}/{len(runs_needing_summary)}] {run['agent']} x {run['test']}: {summary[:80]}...")
        except Exception as e:
            print(f"  [{i}/{len(runs_needing_summary)}] ERROR for {run['agent']} x {run['test']}: {e}")

    path.write_text(json.dumps(data, indent=2, default=str))
    print(f"\nSummaries written to {leaderboard_path}")


if __name__ == "__main__":
    leaderboard_path = sys.argv[1] if len(sys.argv) > 1 else "web/static/leaderboard.json"
    generate_summaries(leaderboard_path)
