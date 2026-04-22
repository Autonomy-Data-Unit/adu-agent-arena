"""LLM-judge scorer that reads agent-produced code from the sandbox.

Scores each dimension on a 1-10 scale rather than a coarse C/P/I grade.
"""

import json
import re

from inspect_ai.model import (
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageUser,
    GenerateConfig,
    ModelOutput,
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


@scorer(
    metrics={
        "overall": [mean(), stderr()],
        "correctness": [mean(), stderr()],
        "code_quality": [mean(), stderr()],
    }
)
def judge_scorer(
    archetype: str = "notebook-analysis",
    model: str = "anthropic/claude-opus-4-7",
) -> Scorer:
    """Score by reading agent-produced code and grading each dimension 1-10."""

    dims = DIMENSIONS.get(archetype, DIMENSIONS["notebook-analysis"])

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

        # Build dimension descriptions and JSON template
        dim_text = "\n".join(f"- **{name}**: {desc}" for name, desc in dims)
        json_fields = ",\n".join(f'  "{name}": <1-10>' for name, _ in dims)

        prompt = JUDGE_PROMPT.format(
            task_prompt=state.input_text[:4000],
            code=code_text[:10000],
            target=target.text,
            dimensions=dim_text,
            json_template=json_fields,
        )

        # Call the judge model
        judge_model = get_model(model)
        response = await judge_model.generate(
            [
                ChatMessageSystem(content="You are an expert code reviewer. Respond only with the requested JSON."),
                ChatMessageUser(content=prompt),
            ],
            config=GenerateConfig(),
        )

        output_text = response.choices[0].message.text or ""

        # Parse the JSON response
        scores: dict[str, float] = {}
        reasoning = ""
        try:
            # Extract JSON from markdown code block if present
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", output_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(1))
            else:
                parsed = json.loads(output_text)

            reasoning = parsed.pop("reasoning", "")
            for name, _ in dims:
                raw = parsed.get(name, 5)
                scores[name] = max(0.0, min(10.0, float(raw))) / 10.0  # normalize to 0-1

        except (json.JSONDecodeError, ValueError, TypeError):
            # Fallback: couldn't parse, give middle scores
            reasoning = f"Failed to parse judge response: {output_text[:200]}"
            for name, _ in dims:
                scores[name] = 0.5

        scores["overall"] = sum(scores.values()) / len(scores)

        return Score(
            value=scores,
            explanation=reasoning,
        )

    return score
