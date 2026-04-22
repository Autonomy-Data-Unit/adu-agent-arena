"""Scorer for Excel output files with multiple sheets."""

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
        "sheet_structure": [mean(), stderr()],
        "numeric": [mean(), stderr()],
        "overall": [mean(), stderr()],
    }
)
def excel_scorer() -> Scorer:
    """Score based on Excel output checks declared in sample metadata."""

    async def score(state: TaskState, target: Target) -> Score:
        checks: dict[str, Any] = state.metadata.get("checks", {})
        excel = checks.get("excel_checks", {})
        if not excel:
            return Score(value={"overall": 0.0}, explanation="No excel_checks in metadata")

        sb = sandbox()
        results: dict[str, float] = {}
        explanations: list[str] = []
        file_path = excel["file"]

        # File existence
        r = await sb.exec(
            ["python3", "-c", f"import os; print(os.path.exists('{file_path}'))"],
            timeout=10,
        )
        if not (r.success and r.stdout.strip() == "True"):
            results["file_exists"] = 0.0
            results["sheet_structure"] = 0.0
            results["numeric"] = 0.0
            results["overall"] = 0.0
            return Score(
                value=results,
                explanation=f"Output file not found: {file_path}",
            )
        results["file_exists"] = 1.0

        # Check each sheet
        structure_scores: list[float] = []
        numeric_scores: list[float] = []

        for sheet_name, sheet_checks in excel.get("sheets", {}).items():
            # Row count
            r = await sb.exec(
                [
                    "python3", "-c",
                    f"import pandas as pd; "
                    f"df = pd.read_excel('{file_path}', sheet_name='{sheet_name}'); "
                    f"print(len(df))",
                ],
                timeout=30,
            )
            if r.success:
                actual = int(r.stdout.strip())
                expected = sheet_checks.get("expected_row_count")
                if expected is not None:
                    tolerance = sheet_checks.get("row_count_tolerance", 0)
                    if abs(actual - expected) <= tolerance:
                        structure_scores.append(1.0)
                    else:
                        structure_scores.append(0.0)
                        explanations.append(
                            f"'{sheet_name}' row count: expected {expected} "
                            f"(+/-{tolerance}), got {actual}"
                        )
            else:
                structure_scores.append(0.0)
                explanations.append(f"Failed to read sheet '{sheet_name}': {r.stderr.strip()}")
                continue

            # Numeric checks
            for nc in sheet_checks.get("numeric_checks", []):
                col = nc["column"]
                agg = nc["aggregation"]
                expected_val = nc["expected"]
                tolerance = nc.get("tolerance", 1.0)

                r = await sb.exec(
                    [
                        "python3", "-c",
                        f"import pandas as pd; "
                        f"df = pd.read_excel('{file_path}', sheet_name='{sheet_name}'); "
                        f"print(df['{col}'].{agg}())",
                    ],
                    timeout=30,
                )
                if r.success:
                    actual_val = float(r.stdout.strip())
                    if abs(actual_val - expected_val) <= tolerance:
                        numeric_scores.append(1.0)
                    else:
                        numeric_scores.append(0.0)
                        explanations.append(
                            f"'{sheet_name}'.'{col}'.{agg}(): "
                            f"expected {expected_val} (+/-{tolerance}), got {actual_val}"
                        )
                else:
                    numeric_scores.append(0.0)
                    explanations.append(
                        f"Numeric check failed for '{sheet_name}'.'{col}': {r.stderr.strip()}"
                    )

        results["sheet_structure"] = (
            sum(structure_scores) / len(structure_scores) if structure_scores else 0.0
        )
        results["numeric"] = (
            sum(numeric_scores) / len(numeric_scores) if numeric_scores else 0.0
        )
        results["overall"] = sum(results.values()) / len(results)

        return Score(
            value=results,
            explanation="; ".join(explanations) if explanations else "All checks passed",
        )

    return score
