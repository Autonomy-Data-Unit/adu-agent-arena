#!/usr/bin/env python3
"""Run all arena tests, optionally across multiple models."""

import argparse
import sys

from inspect_ai import eval, eval_set

from adu_arena.tasks.ets_windfall import ets_windfall_calculation
from adu_arena.tasks.medrxiv_scraper import medrxiv_scraper

ALL_TASKS = [
    ets_windfall_calculation,
    medrxiv_scraper,
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all arena tests")
    parser.add_argument(
        "--model",
        nargs="+",
        default=["openai/gpt-4o"],
        help="Model(s) to evaluate (e.g. openai/gpt-4o anthropic/claude-sonnet-4-20250514)",
    )
    parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory for eval logs (default: logs)",
    )
    parser.add_argument(
        "--max-tasks",
        type=int,
        default=2,
        help="Max concurrent tasks (default: 2)",
    )
    args = parser.parse_args()

    tasks = [t() for t in ALL_TASKS]

    if len(args.model) == 1 and len(tasks) == 1:
        # Single model, single task — use simple eval
        logs = eval(tasks, model=args.model[0], log_dir=args.log_dir)
    else:
        # Multiple models or tasks — use eval_set for retry and parallelism
        success, logs = eval_set(
            tasks=tasks,
            model=args.model,
            log_dir=args.log_dir,
            max_tasks=args.max_tasks,
        )
        if not success:
            print("Some evaluations failed.", file=sys.stderr)
            sys.exit(1)

    print(f"\nCompleted {len(logs)} evaluation(s). Logs in {args.log_dir}/")
    print("Run `python scripts/export_leaderboard.py` to update the leaderboard.")


if __name__ == "__main__":
    main()
