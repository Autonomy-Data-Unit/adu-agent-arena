#!/usr/bin/env python3
"""Run arena tests across configured models.

Uses subprocess calls to `inspect eval` for parallelism — each run is
an independent process, avoiding Inspect's single-eval_async limitation.

After each run, validates the result: if the agent made 0 tool calls
and finished in under 30 seconds, or if the session contains provider
errors, the run is considered invalid and automatically retried.
"""

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from inspect_ai.log import read_eval_log

ALL_TASKS = {
    "staffing_analysis": "src/adu_arena/tasks/staffing_analysis.py@staffing_analysis",
    "culture_spending_analysis": "src/adu_arena/tasks/culture_spending.py@culture_spending_analysis",
    "gov_contracts_scraper": "src/adu_arena/tasks/gov_contracts.py@gov_contracts_scraper",
    "csv_deduplicator": "src/adu_arena/tasks/csv_deduplicator.py@csv_deduplicator",
    "boundary_crosswalk_funding": "src/adu_arena/tasks/boundary_crosswalk.py@boundary_crosswalk_funding",
    "climate_price_impact": "src/adu_arena/tasks/climate_price.py@climate_price_impact",
}

MODELS_FILE = Path("models.json")
DEFAULT_PARALLEL = 5
MAX_RETRIES = 3
LOGS_DIR = Path("logs")
SESSIONS_DIR = Path("sessions")


def load_models_config(path: Path) -> dict:
    return json.loads(path.read_text())


def load_models(path: Path) -> list[str]:
    data = load_models_config(path)
    return [m["id"] for m in data["models"]]


def get_completed_counts(log_dir: Path) -> dict[tuple[str, str], int]:
    """Return run counts per (model, task_name) pair."""
    counts: dict[tuple[str, str], int] = {}
    if not log_dir.exists():
        return counts
    for log_file in log_dir.glob("*.eval"):
        try:
            log = read_eval_log(str(log_file), header_only=True)
            if log.status == "success":
                task_name = log.eval.task.split("/")[-1] if "/" in log.eval.task else log.eval.task
                key = (log.eval.model, task_name)
                counts[key] = counts.get(key, 0) + 1
        except Exception:
            continue
    return counts


def validate_run(log_dir: Path, model: str, task_name: str) -> str | None:
    """Check the latest run for infrastructure failures.

    Returns None if valid, or an error description if invalid.
    """
    # Find the latest eval log for this model+task
    candidates = []
    for f in log_dir.glob("*.eval"):
        try:
            log = read_eval_log(str(f), header_only=True)
            t = log.eval.task.split("/")[-1] if "/" in log.eval.task else log.eval.task
            if log.eval.model == model and t == task_name:
                candidates.append(f)
        except Exception:
            continue

    if not candidates:
        return "no log file found"

    latest = sorted(candidates)[-1]
    log = read_eval_log(str(latest))

    if log.status != "success":
        return f"run status: {log.status}"

    # Check timing — runs under 30s with 0% score are suspicious
    duration = None
    if log.stats and log.stats.started_at and log.stats.completed_at:
        from datetime import datetime
        start = datetime.fromisoformat(log.stats.started_at)
        end = datetime.fromisoformat(log.stats.completed_at)
        duration = (end - start).total_seconds()

    # Check for file_exists = 0 (agent produced nothing)
    file_exists = None
    for sample in log.samples or []:
        for scorer_name, score in (sample.scores or {}).items():
            if isinstance(score.value, dict) and "file_exists" in score.value:
                file_exists = score.value["file_exists"]

    if file_exists == 0.0 and duration is not None and duration < 30:
        # Check session for provider errors
        session_error = _check_session_for_errors(model, task_name)
        if session_error:
            # Delete the invalid log
            latest.unlink()
            return f"infrastructure failure ({session_error})"

    return None


def _check_session_for_errors(model: str, task_name: str) -> str | None:
    """Check the session JSONL for provider/infrastructure errors."""
    from adu_arena.scorers.judge import DIMENSIONS  # just to get archetype mapping

    archetype_map = {
        "staffing_analysis": "pipeline-stage",
        "culture_spending_analysis": "notebook-analysis",
        "gov_contracts_scraper": "scrape-and-structure",
        "csv_deduplicator": "full-project-reproduction",
    }

    if "/" in model:
        provider, model_id = model.split("/", 1)
    else:
        provider, model_id = model, model

    archetype = archetype_map.get(task_name, "unknown")
    safe_model_id = model_id.replace("/", "_")
    pattern = f"{provider}_{safe_model_id}_{archetype}_*.jsonl"

    matches = sorted(SESSIONS_DIR.glob(pattern))
    if not matches:
        return None

    session_file = matches[-1]
    try:
        for line in open(session_file):
            event = json.loads(line)
            if event.get("type") == "message_end":
                msg = event.get("message", {})
                if msg.get("stopReason") == "error":
                    error_msg = msg.get("errorMessage", "")
                    if any(phrase in error_msg.lower() for phrase in [
                        "provider returned error",
                        "no endpoints found",
                        "operation was aborted",
                        "tool use",
                        "rate limit",
                        "timeout",
                    ]):
                        return error_msg[:100]
    except Exception:
        pass

    return None


def run_single(model: str, task_spec: str, log_dir: str) -> tuple[str, str, bool, str]:
    """Run one model+test via subprocess."""
    task_name = task_spec.split("@")[-1]
    try:
        result = subprocess.run(
            ["uv", "run", "inspect", "eval", task_spec, "--model", model, "--log-dir", log_dir],
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minutes
        )
        if result.returncode == 0:
            return (model, task_name, True, "success")
        else:
            err = result.stderr.strip().split("\n")[-1] if result.stderr else "unknown error"
            return (model, task_name, False, err[:200])
    except subprocess.TimeoutExpired:
        return (model, task_name, False, "timed out after 30 minutes")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run arena tests across models")
    parser.add_argument("--model", nargs="+", default=None, help="Model(s) to run (default: all from models.json)")
    parser.add_argument("--test", nargs="+", default=None, help="Test(s) to run (default: all)")
    parser.add_argument("--parallel", type=int, default=DEFAULT_PARALLEL, help=f"Max parallel runs (default: {DEFAULT_PARALLEL})")
    parser.add_argument("--min-runs", type=int, default=None, help="Minimum runs per model+test pair (overrides models.json)")
    parser.add_argument("--rerun", action="store_true", help="Run all tests again (accumulates results for averaging)")
    parser.add_argument("--clear", action="store_true", help="Delete all existing results before running")
    parser.add_argument("--list", action="store_true", help="Show what would run without running")
    args = parser.parse_args()

    # Resolve models and min_runs
    models_config = load_models_config(MODELS_FILE) if MODELS_FILE.exists() else None
    if args.model:
        models = args.model
    elif models_config:
        models = [m["id"] for m in models_config["models"]]
        print(f"Loaded {len(models)} models from {MODELS_FILE}")
    else:
        print(f"No --model specified and {MODELS_FILE} not found", file=sys.stderr)
        sys.exit(1)

    min_runs = args.min_runs or (models_config or {}).get("min_runs", 1)

    # Resolve tests
    if args.test:
        tasks = {k: v for k, v in ALL_TASKS.items() if k in args.test}
        if not tasks:
            print(f"No matching tests. Available: {list(ALL_TASKS.keys())}", file=sys.stderr)
            sys.exit(1)
    else:
        tasks = ALL_TASKS

    # Handle --clear: delete all existing results
    if args.clear:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        for f in LOGS_DIR.glob("*.eval"):
            f.unlink()
        for d in LOGS_DIR.iterdir():
            if d.is_dir():
                import shutil
                shutil.rmtree(d)
        print("Cleared all existing results")

    # --rerun: run everything once more (results accumulate)
    # default: top up each pair to min_runs
    if args.rerun or args.clear:
        counts: dict[tuple[str, str], int] = {}
    else:
        counts = get_completed_counts(LOGS_DIR)

    # Build run plan
    plan: list[tuple[str, str, str]] = []
    skipped = 0
    for model in models:
        for task_name, task_spec in tasks.items():
            existing = counts.get((model, task_name), 0)
            needed = max(0, min_runs - existing) if not args.rerun else 1
            if needed == 0:
                skipped += 1
            else:
                for _ in range(needed):
                    plan.append((model, task_name, task_spec))

    print(f"\n{len(plan)} runs to do, {skipped} pairs already at {min_runs}+ runs")

    if args.list:
        for model, task_name, _ in plan:
            print(f"  {model} x {task_name}")
        return

    if not plan:
        print("Nothing to run. Use --rerun to add more, or increase --min-runs.")
        return

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Run with retries for infrastructure failures
    for attempt in range(1, MAX_RETRIES + 1):
        if not plan:
            break

        label = f"(attempt {attempt}/{MAX_RETRIES})" if attempt > 1 else ""
        print(f"\nRunning {len(plan)} tests with --parallel {args.parallel} {label}\n")

        succeeded = 0
        failed = 0
        total = len(plan)
        retry_plan: list[tuple[str, str, str]] = []

        with ThreadPoolExecutor(max_workers=args.parallel) as executor:
            futures = {
                executor.submit(run_single, model, task_spec, str(LOGS_DIR)): (model, task_name, task_spec)
                for model, task_name, task_spec in plan
            }
            for future in as_completed(futures):
                model, task_name, success, message = future.result()
                _, _, task_spec = futures[future]

                if success:
                    # Validate the run for infrastructure failures
                    invalid_reason = validate_run(LOGS_DIR, model, task_name)
                    if invalid_reason:
                        print(f"  [{succeeded + failed + 1}/{total}] INVALID {model} x {task_name}: {invalid_reason}")
                        retry_plan.append((model, task_name, task_spec))
                        failed += 1
                    else:
                        succeeded += 1
                        print(f"  [{succeeded + failed}/{total}] OK   {model} x {task_name}")
                else:
                    failed += 1
                    print(f"  [{succeeded + failed}/{total}] FAIL {model} x {task_name}: {message}")

        print(f"\nAttempt {attempt}: {succeeded} succeeded, {failed} failed")

        if not retry_plan:
            break

        plan = retry_plan
        print(f"Retrying {len(plan)} infrastructure failures...")

    print(f"\nDone.")


if __name__ == "__main__":
    main()
