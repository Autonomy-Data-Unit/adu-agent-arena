#!/usr/bin/env python3
"""Run arena tests across configured models.

Uses subprocess calls to `inspect eval` for parallelism — each run is
an independent process, avoiding Inspect's single-eval_async limitation.
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
}

MODELS_FILE = Path("models.json")
DEFAULT_PARALLEL = 5
LOGS_DIR = Path("logs")


def load_models(path: Path) -> list[str]:
    data = json.loads(path.read_text())
    return [m["id"] for m in data["models"]]


def get_completed_pairs(log_dir: Path) -> set[tuple[str, str]]:
    """Return (model, task_name) pairs that already succeeded."""
    completed = set()
    if not log_dir.exists():
        return completed
    for log_file in log_dir.glob("*.eval"):
        try:
            log = read_eval_log(str(log_file), header_only=True)
            if log.status == "success":
                task_name = log.eval.task.split("/")[-1] if "/" in log.eval.task else log.eval.task
                completed.add((log.eval.model, task_name))
        except Exception:
            continue
    return completed


def run_single(model: str, task_spec: str, log_dir: str) -> tuple[str, str, bool, str]:
    """Run one model+test via subprocess."""
    result = subprocess.run(
        ["uv", "run", "inspect", "eval", task_spec, "--model", model, "--log-dir", log_dir],
        capture_output=True,
        text=True,
        timeout=900,
    )
    task_name = task_spec.split("@")[-1]
    if result.returncode == 0:
        return (model, task_name, True, "success")
    else:
        # Extract error from stderr
        err = result.stderr.strip().split("\n")[-1] if result.stderr else "unknown error"
        return (model, task_name, False, err[:200])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run arena tests across models")
    parser.add_argument("--model", nargs="+", default=None, help="Model(s) to run (default: all from models.json)")
    parser.add_argument("--test", nargs="+", default=None, help="Test(s) to run (default: all)")
    parser.add_argument("--parallel", type=int, default=DEFAULT_PARALLEL, help=f"Max parallel runs (default: {DEFAULT_PARALLEL})")
    parser.add_argument("--force", action="store_true", help="Clear old results and re-run everything")
    parser.add_argument("--list", action="store_true", help="Show what would run without running")
    args = parser.parse_args()

    # Resolve models
    if args.model:
        models = args.model
    elif MODELS_FILE.exists():
        models = load_models(MODELS_FILE)
        print(f"Loaded {len(models)} models from {MODELS_FILE}")
    else:
        print(f"No --model specified and {MODELS_FILE} not found", file=sys.stderr)
        sys.exit(1)

    # Resolve tests
    if args.test:
        tasks = {k: v for k, v in ALL_TASKS.items() if k in args.test}
        if not tasks:
            print(f"No matching tests. Available: {list(ALL_TASKS.keys())}", file=sys.stderr)
            sys.exit(1)
    else:
        tasks = ALL_TASKS

    # Handle --force: clear logs
    if args.force:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        for f in LOGS_DIR.glob("*.eval"):
            f.unlink()
        for d in LOGS_DIR.iterdir():
            if d.is_dir():
                import shutil
                shutil.rmtree(d)
        print("Cleared old results")
        completed: set[tuple[str, str]] = set()
    else:
        completed = get_completed_pairs(LOGS_DIR)

    # Build run plan
    plan: list[tuple[str, str, str]] = []  # (model, task_name, task_spec)
    skipped = 0
    for model in models:
        for task_name, task_spec in tasks.items():
            if (model, task_name) in completed:
                skipped += 1
            else:
                plan.append((model, task_name, task_spec))

    print(f"\n{len(plan)} runs to do, {skipped} already completed")

    if args.list:
        for model, task_name, _ in plan:
            print(f"  {model} x {task_name}")
        return

    if not plan:
        print("Nothing to run. Use --force to re-run.")
        return

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Running with --parallel {args.parallel}\n")

    succeeded = 0
    failed = 0
    total = len(plan)

    with ThreadPoolExecutor(max_workers=args.parallel) as executor:
        futures = {
            executor.submit(run_single, model, task_spec, str(LOGS_DIR)): (model, task_name)
            for model, task_name, task_spec in plan
        }
        for future in as_completed(futures):
            model, task_name, success, message = future.result()
            if success:
                succeeded += 1
                print(f"  [{succeeded + failed}/{total}] OK   {model} x {task_name}")
            else:
                failed += 1
                print(f"  [{succeeded + failed}/{total}] FAIL {model} x {task_name}: {message}")

    print(f"\nDone: {succeeded} succeeded, {failed} failed")


if __name__ == "__main__":
    main()
