#!/usr/bin/env python3
"""Utilities for viewing and managing test results.

Usage:
    uv run python scripts/results.py show                    # Show all results
    uv run python scripts/results.py show --model qwen       # Filter by model
    uv run python scripts/results.py show --test csv          # Filter by test
    uv run python scripts/results.py delete --model llama     # Delete model's results
    uv run python scripts/results.py delete --run-id abc123   # Delete specific run
    uv run python scripts/results.py delete --invalid         # Delete runs with 0% file_exists
    uv run python scripts/results.py stats                    # Summary statistics
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from inspect_ai.log import read_eval_log

LOGS_DIR = Path("logs")
SESSIONS_DIR = Path("sessions")
SUMMARIES_DIR = Path("summaries")


def load_runs() -> list[dict]:
    """Load all runs from eval logs."""
    runs = []
    for f in sorted(LOGS_DIR.glob("*.eval")):
        try:
            log = read_eval_log(str(f))
            task = log.eval.task.split("/")[-1] if "/" in log.eval.task else log.eval.task
            model = log.eval.model

            duration = None
            if log.stats and log.stats.started_at and log.stats.completed_at:
                start = datetime.fromisoformat(log.stats.started_at)
                end = datetime.fromisoformat(log.stats.completed_at)
                duration = (end - start).total_seconds()

            file_exists = None
            det_overall = None
            judge_overall = None
            for sample in log.samples or []:
                for scorer_name, score in (sample.scores or {}).items():
                    if isinstance(score.value, dict):
                        if "file_exists" in score.value:
                            file_exists = score.value["file_exists"]
                        if "overall" in score.value:
                            if "judge" in scorer_name:
                                judge_overall = score.value["overall"]
                            else:
                                det_overall = score.value["overall"]

            runs.append({
                "file": f,
                "id": log.eval.run_id,
                "model": model,
                "task": task,
                "status": log.status,
                "duration": duration,
                "file_exists": file_exists,
                "det_overall": det_overall,
                "judge_overall": judge_overall,
            })
        except Exception as e:
            runs.append({"file": f, "error": str(e)})
    return runs


def cmd_show(args):
    runs = load_runs()

    # Filter
    if args.model:
        runs = [r for r in runs if args.model.lower() in r.get("model", "").lower()]
    if args.test:
        runs = [r for r in runs if args.test.lower() in r.get("task", "").lower()]

    if not runs:
        print("No matching runs found.")
        return

    print(f"{'Model':<45} {'Test':<30} {'Det':>5} {'Judge':>5} {'Time':>6} {'Status':<8}")
    print("-" * 105)
    for r in runs:
        if "error" in r:
            print(f"  ERROR reading {r['file'].name}: {r['error']}")
            continue
        model = r["model"].split("/")[-1] if "/" in r["model"] else r["model"]
        det = f"{r['det_overall']*100:.0f}%" if r["det_overall"] is not None else "-"
        judge = f"{r['judge_overall']*100:.0f}%" if r["judge_overall"] is not None else "-"
        time = f"{r['duration']:.0f}s" if r["duration"] else "-"
        fe = "" if r.get("file_exists", 1) >= 1 else " [NO FILES]"
        print(f"{model:<45} {r['task']:<30} {det:>5} {judge:>5} {time:>6} {r['status']:<8}{fe}")


def cmd_delete(args):
    runs = load_runs()

    to_delete = []

    if args.run_id:
        to_delete = [r for r in runs if args.run_id in str(r.get("id", ""))]
    elif args.model:
        to_delete = [r for r in runs if args.model.lower() in r.get("model", "").lower()]
    elif args.test:
        to_delete = [r for r in runs if args.test.lower() in r.get("task", "").lower()]
    elif args.invalid:
        to_delete = [r for r in runs if r.get("file_exists") == 0.0]
    else:
        print("Specify --model, --test, --run-id, or --invalid")
        return

    if not to_delete:
        print("No matching runs to delete.")
        return

    print(f"Will delete {len(to_delete)} run(s):")
    for r in to_delete:
        print(f"  {r.get('model', '?')} x {r.get('task', '?')} ({r['file'].name})")

    if not args.yes:
        confirm = input("\nProceed? [y/N] ")
        if confirm.lower() != "y":
            print("Cancelled.")
            return

    for r in to_delete:
        r["file"].unlink()
        # Also delete summary if it exists
        run_id = r.get("id", "")
        summary_file = SUMMARIES_DIR / f"{run_id}.txt"
        if summary_file.exists():
            summary_file.unlink()
        print(f"  Deleted {r['file'].name}")

    print(f"\nDeleted {len(to_delete)} run(s).")


def cmd_stats(args):
    runs = load_runs()
    valid = [r for r in runs if "error" not in r]

    models = sorted(set(r["model"] for r in valid))
    tasks = sorted(set(r["task"] for r in valid))

    print(f"\n{len(valid)} runs across {len(models)} models and {len(tasks)} tests\n")

    # Matrix
    header = f"{'Model':<45}"
    for t in tasks:
        short = t[:12]
        header += f" {short:>12}"
    header += f" {'Avg':>6}"
    print(header)
    print("-" * len(header))

    for model in models:
        model_short = model.split("/")[-1] if "/" in model else model
        row = f"{model_short:<45}"
        scores = []
        for task in tasks:
            matching = [r for r in valid if r["model"] == model and r["task"] == task]
            if matching:
                det = matching[0].get("det_overall")
                judge = matching[0].get("judge_overall")
                if det is not None and judge is not None:
                    combined = (det + judge) / 2
                    scores.append(combined)
                    row += f" {combined*100:>11.0f}%"
                elif det is not None:
                    scores.append(det)
                    row += f" {det*100:>11.0f}%"
                else:
                    row += f" {'?':>12}"
            else:
                row += f" {'-':>12}"

        avg = sum(scores) / len(scores) if scores else 0
        row += f" {avg*100:>5.0f}%"
        print(row)


def main():
    parser = argparse.ArgumentParser(description="Manage test results")
    sub = parser.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Show all results")
    show.add_argument("--model", help="Filter by model name (substring match)")
    show.add_argument("--test", help="Filter by test name (substring match)")

    delete = sub.add_parser("delete", help="Delete results")
    delete.add_argument("--model", help="Delete all runs for a model")
    delete.add_argument("--test", help="Delete all runs for a test")
    delete.add_argument("--run-id", help="Delete a specific run by ID")
    delete.add_argument("--invalid", action="store_true", help="Delete runs where agent produced no files")
    delete.add_argument("--yes", action="store_true", help="Skip confirmation")

    sub.add_parser("stats", help="Summary statistics")

    args = parser.parse_args()
    if args.command == "show":
        cmd_show(args)
    elif args.command == "delete":
        cmd_delete(args)
    elif args.command == "stats":
        cmd_stats(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
