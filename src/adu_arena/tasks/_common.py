"""Shared helpers for task definitions."""

import json
from pathlib import Path

from inspect_ai.dataset import MemoryDataset, Sample


def load_task_dataset(test_dir: Path) -> MemoryDataset:
    """Load dataset from a test directory, mapping workspace files into Sample.files."""
    prompt = (test_dir / "prompt.md").read_text()
    raw = json.loads((test_dir / "dataset.json").read_text())

    # Map workspace files to container paths
    workspace = test_dir / "workspace"
    files: dict[str, str] = {}
    if workspace.exists():
        for f in workspace.rglob("*"):
            if f.is_file():
                container_path = "/workspace/" + str(f.relative_to(workspace))
                files[container_path] = str(f)

    return MemoryDataset([
        Sample(
            input=prompt,
            target=entry["target"],
            metadata=entry["metadata"],
            files=files,
        )
        for entry in raw
    ])
