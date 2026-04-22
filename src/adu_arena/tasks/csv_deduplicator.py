"""Company Record Deduplicator test.

Archetype: full-project-reproduction
Synthetic data themed around UK Companies House records.
"""

import json
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample

from adu_arena.agents.pi_agent import pi_coding_agent
from adu_arena.scorers.deterministic import deterministic_scorer
from adu_arena.scorers.judge import judge_scorer

TEST_DIR = Path(__file__).parent.parent.parent.parent / "tests" / "csv-deduplicator"


def _load_dataset() -> MemoryDataset:
    prompt = (TEST_DIR / "prompt.md").read_text()
    raw = json.loads((TEST_DIR / "dataset.json").read_text())
    return MemoryDataset([
        Sample(input=prompt, target=entry["target"], metadata=entry["metadata"])
        for entry in raw
    ])


@task
def csv_deduplicator(timeout: int = 600) -> Task:
    return Task(
        dataset=_load_dataset(),
        solver=pi_coding_agent(timeout=timeout),
        scorer=[
            deterministic_scorer(),
            judge_scorer(archetype="full-project-reproduction"),
        ],
        sandbox=("docker", str(TEST_DIR / "compose.yaml")),
        time_limit=timeout + 60,
        token_limit=300_000,
    )
