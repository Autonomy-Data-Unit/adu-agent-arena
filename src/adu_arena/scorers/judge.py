"""LLM-judge scorer using multiple judge models, each run N times.

Configuration is read from models.json:
  "judges": {
    "models": ["anthropic/claude-opus-4-7", "openai/gpt-5.4"],
    "runs_per_judge": 3
  }

The final score for each dimension is the mean across all judge
evaluations (models × runs_per_judge).
"""

import asyncio
import json
import re
from pathlib import Path

from inspect_ai.model import (
    ChatMessageSystem,
    ChatMessageUser,
    GenerateConfig,
    get_model,
)
from inspect_ai.scorer import (
    Score,
    Scorer,
    Target,
    mean,
    scorer,
    stderr,
)
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox

DIMENSIONS = {
    "scrape-and-structure": [
        ("correctness", "Does the scraper extract the right data from the HTML?"),
        ("robustness", "Does it handle edge cases (missing fields, whitespace, HTML entities)?"),
        ("structure", "Is the output well-structured, validated, and in the correct format?"),
        ("code_quality", "Is the code clean, readable, and idiomatic Python?"),
    ],
    "notebook-analysis": [
        ("correctness", "Does the code produce the right numerical results?"),
        ("methodology", "Is the data processing approach sound (correct merges, aggregations, formulas)?"),
        ("completeness", "Does it address all parts of the task specification?"),
        ("code_quality", "Is the code clean, readable, and well-structured?"),
    ],
    "pipeline-stage": [
        ("correctness", "Does the transformation produce the expected output?"),
        ("methodology", "Is the data transformation approach sound and appropriate?"),
        ("completeness", "Does it handle all the steps described in the specification?"),
        ("code_quality", "Is the code clean, readable, and well-structured?"),
    ],
    "full-project-reproduction": [
        ("correctness", "Does the code work as specified?"),
        ("architecture", "Is the code well-organized and modular?"),
        ("edge_cases", "Are edge cases handled appropriately?"),
        ("code_quality", "Is the code clean, readable, and idiomatic Python?"),
    ],
}

JUDGE_PROMPT = """\
You are an expert code reviewer evaluating agent-produced code.

## Task given to the agent
{task_prompt}

## Code produced by the agent
{code}

## Expected outcome
{target}

## Instructions

Score the code on each dimension below from 1 to 10, where:
- 1-3: Fundamentally broken or incorrect
- 4-5: Partially works but has significant issues
- 6-7: Works correctly with minor issues
- 8-9: Works well, clean and robust
- 10: Excellent, nothing to improve

Dimensions:
{dimensions}

Respond with ONLY a JSON object in this exact format (no other text before or after):
```json
{{
{json_template}
  "reasoning": "Brief explanation of your scores (2-4 sentences)"
}}
```
"""

MODELS_FILE = Path("models.json")


def _load_judge_config() -> tuple[list[str], int]:
    """Load judge models and runs_per_judge from models.json."""
    if MODELS_FILE.exists():
        data = json.loads(MODELS_FILE.read_text())
        judges = data.get("judges", {})
        models = judges.get("models", ["anthropic/claude-opus-4-7"])
        runs = judges.get("runs_per_judge", 1)
        return models, runs
    return ["anthropic/claude-opus-4-7"], 1


def _parse_judge_response(output_text: str, dims: list[tuple[str, str]]) -> tuple[dict[str, float], str]:
    """Parse a judge's JSON response into scores and reasoning."""
    try:
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", output_text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(1))
        else:
            parsed = json.loads(output_text)

        reasoning = parsed.pop("reasoning", "")
        scores: dict[str, float] = {}
        for name, _ in dims:
            raw = parsed.get(name, 5)
            scores[name] = max(0.0, min(10.0, float(raw))) / 10.0
        return scores, reasoning

    except (json.JSONDecodeError, ValueError, TypeError):
        return {name: 0.5 for name, _ in dims}, f"Failed to parse: {output_text[:200]}"


@scorer(
    metrics={
        "overall": [mean(), stderr()],
        "correctness": [mean(), stderr()],
        "code_quality": [mean(), stderr()],
    }
)
def judge_scorer(
    archetype: str = "notebook-analysis",
) -> Scorer:
    """Score by reading agent-produced code and grading with multiple judges."""

    dims = DIMENSIONS.get(archetype, DIMENSIONS["notebook-analysis"])
    judge_models, runs_per_judge = _load_judge_config()

    async def _single_judge_call(
        judge_model_name: str, prompt: str
    ) -> tuple[dict[str, float], str]:
        """Make a single judge API call."""
        judge_model = get_model(judge_model_name)
        response = await judge_model.generate(
            [
                ChatMessageSystem(
                    content="You are an expert code reviewer. Respond only with the requested JSON."
                ),
                ChatMessageUser(content=prompt),
            ],
            config=GenerateConfig(),
        )
        output_text = response.choices[0].message.text or ""
        return _parse_judge_response(output_text, dims)

    async def score(state: TaskState, target: Target) -> Score:
        sb = sandbox()

        # Discover .py files the agent created
        r = await sb.exec(
            ["find", "/workspace", "-name", "*.py", "-not", "-path", "*/.*"],
            timeout=10,
        )
        paths = [p.strip() for p in (r.stdout or "").splitlines() if p.strip()]

        # Read all code files
        code_parts: list[str] = []
        for path in paths:
            try:
                content = await sb.read_file(path)
                code_parts.append(f"### {path}\n```python\n{content}\n```")
            except Exception:
                continue

        if not code_parts:
            return Score(
                value={d[0]: 0.0 for d in dims} | {"overall": 0.0},
                explanation="No code files found in the sandbox",
            )

        code_text = "\n\n".join(code_parts)

        # Build the judge prompt
        dim_text = "\n".join(f"- **{name}**: {desc}" for name, desc in dims)
        json_fields = ",\n".join(f'  "{name}": <1-10>' for name, _ in dims)
        prompt = JUDGE_PROMPT.format(
            task_prompt=state.input_text[:4000],
            code=code_text[:10000],
            target=target.text,
            dimensions=dim_text,
            json_template=json_fields,
        )

        # Run all judges × runs_per_judge concurrently
        async def _labeled_call(model_name: str, run_i: int):
            label = model_name.split("/")[-1]
            try:
                scores_i, reasoning_i = await _single_judge_call(model_name, prompt)
                return scores_i, f"**{label} (run {run_i + 1})**: {reasoning_i}"
            except Exception as e:
                return None, f"**{label} (run {run_i + 1})**: ERROR: {e}"

        tasks = [
            _labeled_call(model_name, run_i)
            for model_name in judge_models
            for run_i in range(runs_per_judge)
        ]
        results = await asyncio.gather(*tasks)

        all_scores: list[dict[str, float]] = []
        all_reasoning: list[str] = []
        for scores_i, reasoning_i in results:
            if scores_i is not None:
                all_scores.append(scores_i)
            all_reasoning.append(reasoning_i)

        if not all_scores:
            return Score(
                value={d[0]: 0.0 for d in dims} | {"overall": 0.0},
                explanation="All judge calls failed:\n" + "\n".join(all_reasoning),
            )

        # Average across all evaluations
        avg_scores: dict[str, float] = {}
        for name, _ in dims:
            vals = [s[name] for s in all_scores if name in s]
            avg_scores[name] = sum(vals) / len(vals) if vals else 0.0

        avg_scores["overall"] = sum(avg_scores.values()) / len(avg_scores)

        explanation = (
            f"Averaged across {len(all_scores)} evaluations "
            f"({len(judge_models)} judges × {runs_per_judge} runs)\n\n"
            + "\n\n".join(all_reasoning)
        )

        return Score(
            value=avg_scores,
            explanation=explanation,
        )

    return score
