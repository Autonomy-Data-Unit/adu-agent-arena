"""ETS Windfall Calculation test.

Archetype: notebook-analysis
Complexity: Simple
Source: Autonomy-Data-Unit/2024_10_emissions-trading-registry-analysis
"""

import json
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample

from adu_arena.agents.pi_agent import pi_coding_agent
from adu_arena.scorers.excel import excel_scorer
from adu_arena.scorers.judge import judge_scorer

TEST_DIR = Path(__file__).parent.parent.parent.parent / "tests" / "ets-windfall-calculation"


def _load_dataset() -> MemoryDataset:
    prompt = (TEST_DIR / "prompt.md").read_text()
    raw = json.loads((TEST_DIR / "dataset.json").read_text())
    samples = [
        Sample(
            input=prompt,
            target=entry["target"],
            metadata=entry["metadata"],
        )
        for entry in raw
    ]
    return MemoryDataset(samples)


@task
def ets_windfall_calculation(timeout: int = 900) -> Task:
    return Task(
        dataset=_load_dataset(),
        solver=pi_coding_agent(timeout=timeout),
        scorer=[
            excel_scorer(),
            judge_scorer(archetype="notebook-analysis"),
        ],
        sandbox=("docker", str(TEST_DIR / "compose.yaml")),
        time_limit=timeout + 60,
        token_limit=500_000,
    )
