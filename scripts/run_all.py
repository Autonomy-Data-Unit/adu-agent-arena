#!/usr/bin/env python3
"""Run arena tests across configured models, skipping already-completed runs."""

import argparse
import json
import sys
from pathlib import Path

from inspect_ai import eval, eval_set
from inspect_ai.log import read_eval_log

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
DEFAULT_PARALLEL = 5


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

    for log_file in log_path.rglob("*.eval"):
        try:
            log = read_eval_log(str(log_file), header_only=True)
            if log.status == "success":
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
        "--parallel",
        type=int,
        default=DEFAULT_PARALLEL,
        help=f"Max parallel runs (default: {DEFAULT_PARALLEL})",
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

    # Build run plan — group by model since eval_set handles multi-model natively
    plan_models = set()
    plan_tasks = set()
    skipped = 0
    total = 0
    for model in models:
        for task_name in tasks:
            if (model, task_name) in completed:
                skipped += 1
            else:
                plan_models.add(model)
                plan_tasks.add(task_name)
                total += 1

    print(f"\n{total} runs to do, {skipped} already completed")

    if args.list:
        for model in sorted(plan_models):
            for task_name in sorted(plan_tasks):
                if (model, task_name) not in completed:
                    print(f"  {model} x {task_name}")
        if skipped:
            print(f"\n{skipped} combinations already in {args.log_dir}/")
        return

    if total == 0:
        print("Nothing to run — all combinations already completed.")
        print("Use --force to re-run, or add new models to models.json")
        return

    # Build task instances for all needed tasks
    task_instances = [tasks[name]() for name in sorted(plan_tasks)]
    model_list = sorted(plan_models)

    from datetime import datetime
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_log_dir = Path(args.log_dir) / f"run_{run_id}"
    run_log_dir.mkdir(parents=True, exist_ok=True)

    print(f"Running {len(model_list)} models x {len(task_instances)} tests with --parallel {args.parallel}")
    print(f"Logs: {run_log_dir}\n")

    success, logs = eval_set(
        tasks=task_instances,
        model=model_list,
        log_dir=str(run_log_dir),
        max_tasks=args.parallel,
    )

    # Copy logs to parent dir so export_leaderboard can find them all
    for log_file in run_log_dir.glob("*.eval"):
        dest = Path(args.log_dir) / log_file.name
        if not dest.exists():
            import shutil
            shutil.copy2(log_file, dest)

    succeeded = sum(1 for l in logs if l.status == "success")
    failed = sum(1 for l in logs if l.status != "success")

    print(f"\nDone: {succeeded} succeeded, {failed} failed")
    if not success:
        print("Some evaluations failed.", file=sys.stderr)
    print("Run `uv run python scripts/export_leaderboard.py` to update the leaderboard.")


if __name__ == "__main__":
    main()
