#!/usr/bin/env python3
"""Export Inspect AI eval logs to leaderboard.json for the SvelteKit app."""

import json
import sys
from pathlib import Path

import pandas as pd
from inspect_ai.analysis import evals_df
from inspect_ai.log import read_eval_log


ARCHETYPE_MAP = {
    "staffing_analysis": "pipeline-stage",
    "culture_spending_analysis": "notebook-analysis",
    "gov_contracts_scraper": "scrape-and-structure",
    "csv_deduplicator": "full-project-reproduction",
}


def extract_session_cost(sessions_dir: Path, model: str, task_name: str) -> dict | None:
    """Extract token usage and cost from a pi session JSONL file."""
    # Build the expected session filename
    if "/" in model:
        provider, model_id = model.split("/", 1)
    else:
        provider, model_id = model, model

    archetype = ARCHETYPE_MAP.get(task_name, "unknown")
    safe_model_id = model_id.replace("/", "_")
    session_file = sessions_dir / f"{provider}_{safe_model_id}_{archetype}_1.jsonl"

    if not session_file.exists():
        return None

    total_input = 0
    total_output = 0
    total_cost = 0.0

    try:
        for line in open(session_file):
            event = json.loads(line)
            if event.get("type") == "message_end":
                msg = event.get("message", {})
                usage = msg.get("usage")
                if usage and msg.get("role") == "assistant":
                    total_input += usage.get("input", 0)
                    total_output += usage.get("output", 0)
                    cost = usage.get("cost", {})
                    if isinstance(cost, dict):
                        total_cost += cost.get("total", 0)
                    elif isinstance(cost, (int, float)):
                        total_cost += cost
    except Exception:
        return None

    if total_input == 0 and total_output == 0:
        return None

    return {
        "input_tokens": total_input,
        "output_tokens": total_output,
        "total_cost": round(total_cost, 4),
    }


def extract_log_details(log_path: str) -> tuple[dict[str, dict], float | None]:
    """Read an eval log and extract per-scorer explanations and duration."""
    details: dict[str, dict] = {}
    duration: float | None = None
    try:
        log = read_eval_log(log_path)
        for sample in log.samples or []:
            for scorer_name, score in (sample.scores or {}).items():
                details[scorer_name] = {
                    "value": score.value if isinstance(score.value, (str, int, float, dict)) else str(score.value),
                    "explanation": score.explanation or "",
                }
        if log.stats and log.stats.started_at and log.stats.completed_at:
            from datetime import datetime
            start = datetime.fromisoformat(log.stats.started_at)
            end = datetime.fromisoformat(log.stats.completed_at)
            duration = (end - start).total_seconds()
    except Exception:
        pass
    return details, duration


SUMMARIES_DIR = Path("summaries")


def export(log_dir: str = "logs", output: str = "web/static/leaderboard.json") -> None:
    log_path = Path(log_dir)
    if not log_path.exists():
        print(f"Log directory not found: {log_dir}", file=sys.stderr)
        sys.exit(1)

    df, errors = evals_df(log_dir, strict=False)
    if df.empty:
        print("No eval logs found.", file=sys.stderr)
        sys.exit(1)

    if errors:
        for e in errors:
            print(f"Warning: {e}", file=sys.stderr)

    # Build leaderboard structure
    leaderboard: dict = {
        "generated_at": pd.Timestamp.now().isoformat(),
        "agents": [],
        "tests": [],
        "runs": [],
    }

    # Extract unique agents and tests
    agents = set()
    tests = set()

    for _, row in df.iterrows():
        model = str(row.get("model", "unknown"))
        task_name = str(row.get("task_name", "unknown"))
        agents.add(model)
        tests.add(task_name)

        run = {
            "id": str(row.get("eval_id", "")),
            "agent": model,
            "test": task_name,
            "timestamp": str(row.get("created", "")),
            "status": str(row.get("status", "")),
            "scores": {},
            "score_details": {},
        }

        # Extract score columns (they vary by scorer)
        for col in df.columns:
            if col.startswith("score_") or col.startswith("metrics_"):
                val = row.get(col)
                if pd.notna(val):
                    run["scores"][col] = float(val) if isinstance(val, (int, float)) else str(val)

        # Cost and time
        for field in ["total_time", "total_cost", "input_tokens", "output_tokens"]:
            val = row.get(field)
            if pd.notna(val):
                run[field] = float(val) if isinstance(val, (int, float)) else str(val)

        # Read detailed explanations and duration from the eval log
        log_file = row.get("log")
        if pd.notna(log_file):
            score_details, duration = extract_log_details(str(log_file))
            run["score_details"] = score_details
            if duration is not None:
                run["total_time"] = round(duration, 1)

        # Extract cost from pi session file
        sessions_dir = Path("sessions")
        if sessions_dir.exists():
            cost_data = extract_session_cost(sessions_dir, model, task_name)
            if cost_data:
                run["input_tokens"] = cost_data["input_tokens"]
                run["output_tokens"] = cost_data["output_tokens"]
                run["total_cost"] = cost_data["total_cost"]

        # Load summary from summaries/ directory
        summary_file = SUMMARIES_DIR / f"{run['id']}.txt"
        if summary_file.exists():
            run["summary"] = summary_file.read_text()

        leaderboard["runs"].append(run)

    leaderboard["agents"] = sorted(agents)
    leaderboard["tests"] = sorted(tests)

    # Load test descriptions from DESCRIPTION.md files
    tests_dir = Path("tests")
    test_descriptions: dict[str, str] = {}
    # Map task_name (e.g. "staffing_analysis") to dir name (e.g. "staffing-analysis")
    if tests_dir.exists():
        for test_dir in tests_dir.iterdir():
            desc_file = test_dir / "DESCRIPTION.md"
            if desc_file.exists():
                # Convert dir name to task name: "staffing-analysis" -> "staffing_analysis"
                task_name = test_dir.name.replace("-", "_")
                test_descriptions[task_name] = desc_file.read_text()
    leaderboard["test_descriptions"] = test_descriptions

    # Aggregate per agent-test pair
    aggregates = []
    for agent in sorted(agents):
        for test in sorted(tests):
            mask = (df.get("model") == agent) & (df.get("task_name") == test)
            subset = df[mask]
            if subset.empty:
                continue

            agg = {
                "agent": agent,
                "test": test,
                "run_count": len(subset),
            }

            # Aggregate numeric score columns only
            for col in df.columns:
                if not (col.startswith("score_") or col.startswith("metrics_")):
                    continue
                # Skip non-numeric score columns (e.g. score_headline_name)
                if col.endswith("_name") or col.endswith("_metric"):
                    continue
                vals = pd.to_numeric(subset[col], errors="coerce").dropna()
                if not vals.empty:
                    agg[f"{col}_mean"] = round(float(vals.mean()), 4)
                    agg[f"{col}_std"] = round(float(vals.std()), 4) if len(vals) > 1 else 0.0

            # Aggregate cost/time from the runs we built (not from evals_df)
            matching_runs = [
                r for r in leaderboard["runs"]
                if r["agent"] == agent and r["test"] == test
            ]
            for field in ["total_time", "total_cost"]:
                vals = [r[field] for r in matching_runs if r.get(field) is not None]
                if vals:
                    agg[f"{field}_mean"] = round(sum(vals) / len(vals), 4)

            aggregates.append(agg)

    leaderboard["aggregates"] = aggregates

    # Write output
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(leaderboard, indent=2, default=str))
    print(f"Leaderboard exported to {out_path} ({len(leaderboard['runs'])} runs)")


if __name__ == "__main__":
    log_dir = sys.argv[1] if len(sys.argv) > 1 else "logs"
    output = sys.argv[2] if len(sys.argv) > 2 else "web/static/leaderboard.json"
    export(log_dir, output)
