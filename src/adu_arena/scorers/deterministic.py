"""Reusable deterministic scorer driven by sample metadata.

Checks are declared in sample.metadata["checks"] and can include:
- expected_files: list of paths that must exist
- csv_schema: {file, columns} — column names must match
- row_count: {file, expected, tolerance?} — row count check
- numeric_checks: [{file, column, aggregation, expected, tolerance}]
- content_present: {file, strings} — strings that must appear
- content_absent: {file, strings} — strings that must NOT appear
"""

from typing import Any

from inspect_ai.scorer import (
    Score,
    Scorer,
    Target,
    accuracy,
    mean,
    scorer,
    stderr,
)
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox


@scorer(
    metrics={
        "file_exists": [accuracy(), stderr()],
        "csv_schema": [accuracy(), stderr()],
        "row_count": [accuracy(), stderr()],
        "numeric": [mean(), stderr()],
        "content": [accuracy(), stderr()],
        "overall": [mean(), stderr()],
    }
)
def deterministic_scorer() -> Scorer:
    """Score based on deterministic checks declared in sample metadata."""

    async def score(state: TaskState, target: Target) -> Score:
        checks: dict[str, Any] = state.metadata.get("checks", {})
        results: dict[str, float] = {}
        explanations: list[str] = []
        sb = sandbox()

        # File existence checks
        if "expected_files" in checks:
            passed = 0
            for path in checks["expected_files"]:
                try:
                    await sb.read_file(path)
                    passed += 1
                except Exception:
                    explanations.append(f"Missing file: {path}")
            total = len(checks["expected_files"])
            results["file_exists"] = passed / total if total else 1.0

        # CSV schema check
        if "csv_schema" in checks:
            spec = checks["csv_schema"]
            r = await sb.exec(
                [
                    "python3",
                    "-c",
                    f"import pandas as pd; df = pd.read_csv('{spec['file']}'); "
                    f"print(','.join(sorted(df.columns)))",
                ],
                timeout=30,
            )
            expected = ",".join(sorted(spec["columns"]))
            if r.success and r.stdout.strip() == expected:
                results["csv_schema"] = 1.0
            else:
                results["csv_schema"] = 0.0
                actual = r.stdout.strip() if r.success else r.stderr.strip()
                explanations.append(
                    f"CSV schema mismatch: expected {expected}, got {actual}"
                )

        # Row count check
        if "row_count" in checks:
            spec = checks["row_count"]
            r = await sb.exec(
                [
                    "python3",
                    "-c",
                    f"import pandas as pd; print(len(pd.read_csv('{spec['file']}')))",
                ],
                timeout=30,
            )
            if r.success:
                actual_count = int(r.stdout.strip())
                tolerance = spec.get("tolerance", 0)
                if abs(actual_count - spec["expected"]) <= tolerance:
                    results["row_count"] = 1.0
                else:
                    results["row_count"] = 0.0
                    explanations.append(
                        f"Row count: expected {spec['expected']} "
                        f"(+/-{tolerance}), got {actual_count}"
                    )
            else:
                results["row_count"] = 0.0
                explanations.append(f"Row count check failed: {r.stderr.strip()}")

        # Numeric checks
        if "numeric_checks" in checks:
            scores = []
            for spec in checks["numeric_checks"]:
                agg = spec["aggregation"]
                r = await sb.exec(
                    [
                        "python3",
                        "-c",
                        f"import pandas as pd; "
                        f"df = pd.read_csv('{spec['file']}'); "
                        f"print(df['{spec['column']}'].{agg}())",
                    ],
                    timeout=30,
                )
                if r.success:
                    actual = float(r.stdout.strip())
                    tolerance = spec.get("tolerance", 0.01)
                    if abs(actual - spec["expected"]) <= tolerance:
                        scores.append(1.0)
                    else:
                        scores.append(0.0)
                        explanations.append(
                            f"Numeric {spec['column']}.{agg}(): "
                            f"expected {spec['expected']} "
                            f"(+/-{tolerance}), got {actual}"
                        )
                else:
                    scores.append(0.0)
                    explanations.append(
                        f"Numeric check failed for {spec['column']}: "
                        f"{r.stderr.strip()}"
                    )
            results["numeric"] = sum(scores) / len(scores) if scores else 1.0

        # Content present/absent checks
        if "content_present" in checks or "content_absent" in checks:
            content_scores = []

            if "content_present" in checks:
                spec = checks["content_present"]
                try:
                    content = await sb.read_file(spec["file"])
                    for s in spec["strings"]:
                        if s in content:
                            content_scores.append(1.0)
                        else:
                            content_scores.append(0.0)
                            explanations.append(
                                f"Expected string not found: '{s}'"
                            )
                except Exception:
                    content_scores.extend([0.0] * len(spec["strings"]))
                    explanations.append(
                        f"Could not read {spec['file']} for content check"
                    )

            if "content_absent" in checks:
                spec = checks["content_absent"]
                try:
                    content = await sb.read_file(spec["file"])
                    for s in spec["strings"]:
                        if s not in content:
                            content_scores.append(1.0)
                        else:
                            content_scores.append(0.0)
                            explanations.append(
                                f"Unexpected string found: '{s}'"
                            )
                except Exception:
                    # If file doesn't exist, absent strings are trivially absent
                    content_scores.extend([1.0] * len(spec["strings"]))

            results["content"] = (
                sum(content_scores) / len(content_scores) if content_scores else 1.0
            )

        # Overall score
        if results:
            results["overall"] = sum(results.values()) / len(results)
        else:
            results["overall"] = 0.0

        return Score(
            value=results,
            explanation="; ".join(explanations) if explanations else "All checks passed",
        )

    return score
