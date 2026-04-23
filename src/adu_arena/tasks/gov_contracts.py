"""Government Contract Awards Scraper test.

Archetype: scrape-and-structure
Synthetic data themed around UK government contracts.
"""

from pathlib import Path

from inspect_ai import Task, task

from adu_arena.agents.pi_agent import pi_coding_agent
from adu_arena.scorers.deterministic import deterministic_scorer
from adu_arena.scorers.judge import judge_scorer
from adu_arena.tasks._common import load_task_dataset

TEST_DIR = Path(__file__).parent.parent.parent.parent / "tests" / "gov-contracts-scraper"


@task
def gov_contracts_scraper(timeout: int = 600) -> Task:
    return Task(
        dataset=load_task_dataset(TEST_DIR),
        solver=pi_coding_agent(timeout=timeout),
        scorer=[
            deterministic_scorer(),
            judge_scorer(archetype="scrape-and-structure"),
        ],
        sandbox=("docker", str(TEST_DIR / "compose.yaml")),
        time_limit=timeout + 60,
        token_limit=300_000,
    )
