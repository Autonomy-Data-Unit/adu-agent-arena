#!/usr/bin/env python3
"""Export Inspect AI eval logs to leaderboard.json for the SvelteKit app."""

import json
import sys
from pathlib import Path

import pandas as pd
from inspect_ai.analysis import evals_df
from inspect_ai.log import read_eval_log


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

        leaderboard["runs"].append(run)

    leaderboard["agents"] = sorted(agents)
    leaderboard["tests"] = sorted(tests)

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

            # Aggregate cost/time
            for field in ["total_time", "total_cost"]:
                vals = pd.to_numeric(subset.get(field, pd.Series()), errors="coerce").dropna()
                if not vals.empty:
                    agg[f"{field}_mean"] = round(vals.mean(), 2)

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
