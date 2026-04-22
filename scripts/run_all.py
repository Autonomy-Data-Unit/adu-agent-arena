#!/usr/bin/env python3
"""Run arena tests across configured models, skipping already-completed runs."""

import argparse
import json
import sys
from pathlib import Path

from inspect_ai import eval
from inspect_ai.log import list_eval_logs, read_eval_log

from adu_arena.tasks.staffing_analysis import staffing_analysis
from adu_arena.tasks.culture_spending import culture_spending_analysis
from adu_arena.tasks.gov_contracts import gov_contracts_scraper
from adu_arena.tasks.csv_deduplicator import csv_deduplicator

ALL_TASKS = {
    "staffing_analysis": staffing_analysis,
    "culture_spending_analysis": culture_spending_analysis,
    "gov_contracts_scraper": gov_contracts_scraper,
    "csv_deduplicator": csv_deduplicator,
}

MODELS_FILE = Path("models.json")


def load_models(path: Path) -> list[str]:
    """Load model IDs from models.json."""
    data = json.loads(path.read_text())
    return [m["id"] for m in data["models"]]


def get_completed_pairs(log_dir: str) -> set[tuple[str, str]]:
    """Return set of (model, task_name) pairs that have already succeeded."""
    completed = set()
    log_path = Path(log_dir)
    if not log_path.exists():
        return completed

    for log_file in log_path.glob("*.eval"):
        try:
            log = read_eval_log(str(log_file), header_only=True)
            if log.status == "success":
                # Task names in logs may be prefixed (e.g. "adu_arena/csv_deduplicator")
                task_name = log.eval.task.split("/")[-1] if "/" in log.eval.task else log.eval.task
                completed.add((log.eval.model, task_name))
        except Exception:
            continue

    return completed


def main() -> None:
    parser = argparse.ArgumentParser(description="Run arena tests across models")
    parser.add_argument(
        "--model",
        nargs="+",
        default=None,
        help="Specific model(s) to run (default: all from models.json)",
    )
    parser.add_argument(
        "--test",
        nargs="+",
        default=None,
        help="Specific test(s) to run (default: all)",
    )
    parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory for eval logs (default: logs)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run even if results already exist",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Show what would be run without running",
    )
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
        tasks = {name: fn for name, fn in ALL_TASKS.items() if name in args.test}
        if not tasks:
            print(f"No matching tests. Available: {list(ALL_TASKS.keys())}", file=sys.stderr)
            sys.exit(1)
    else:
        tasks = ALL_TASKS

    # Check what's already done
    completed = get_completed_pairs(args.log_dir) if not args.force else set()

    # Build run plan
    plan: list[tuple[str, str]] = []
    skipped = 0
    for model in models:
        for task_name in tasks:
            if (model, task_name) in completed:
                skipped += 1
            else:
                plan.append((model, task_name))

    print(f"\n{len(plan)} runs to do, {skipped} already completed")
    if args.list:
        for model, task_name in plan:
            print(f"  {model} x {task_name}")
        if skipped:
            print(f"\n{skipped} combinations already in {args.log_dir}/")
        return

    if not plan:
        print("Nothing to run — all combinations already completed.")
        print("Use --force to re-run, or add new models to models.json")
        return

    # Run each combination
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    succeeded = 0
    failed = 0

    for i, (model, task_name) in enumerate(plan, 1):
        print(f"\n[{i}/{len(plan)}] {model} x {task_name}")
        try:
            task_fn = tasks[task_name]
            logs = eval(
                tasks=[task_fn()],
                model=model,
                log_dir=args.log_dir,
            )
            if logs and logs[0].status == "success":
                succeeded += 1
            else:
                failed += 1
                print(f"  FAILED: {logs[0].status if logs else 'no logs'}")
        except Exception as e:
            failed += 1
            print(f"  ERROR: {e}")

    print(f"\nDone: {succeeded} succeeded, {failed} failed")
    print("Run `uv run python scripts/export_leaderboard.py` to update the leaderboard.")


if __name__ == "__main__":
    main()
