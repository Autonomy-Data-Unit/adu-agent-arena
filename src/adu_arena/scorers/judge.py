"""LLM-judge scorer that reads agent-produced code from the sandbox."""

from inspect_ai.scorer import (
    Score,
    Scorer,
    Target,
    accuracy,
    model_graded_qa,
    scorer,
    stderr,
)
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox

RUBRICS = {
    "scrape-and-structure": """\
You are evaluating code that scrapes and structures data from web sources.

## Task
{question}

## Agent's code
{answer}

## Expected outcome
{criterion}

## Evaluation criteria

Grade on these dimensions:
1. **Correctness**: Does the scraper extract the right data from the HTML?
2. **Robustness**: Does it handle edge cases (missing fields, whitespace, encoding)?
3. **Structure**: Is the output well-structured and validated?
4. **Code quality**: Is the code clean, readable, and idiomatic Python?

If the code is correct and well-written, grade GRADE: C.
If the code is partially correct or has minor issues, grade GRADE: P.
If the code fails to extract data correctly, grade GRADE: I.

{instructions}
""",
    "notebook-analysis": """\
You are evaluating code that performs data analysis.

## Task
{question}

## Agent's code
{answer}

## Expected outcome
{criterion}

## Evaluation criteria

Grade on these dimensions:
1. **Correctness**: Does the code produce the right numerical results?
2. **Methodology**: Is the data processing approach sound (correct merges, aggregations, formulas)?
3. **Completeness**: Does it address all parts of the task specification?
4. **Code quality**: Is the code clean, readable, and well-structured?

If the code is correct, complete, and well-written, grade GRADE: C.
If the code is partially correct or has minor issues, grade GRADE: P.
If the code is incorrect or fundamentally flawed, grade GRADE: I.

{instructions}
""",
    "pipeline-stage": """\
You are evaluating code that performs a data pipeline transformation.

## Task
{question}

## Agent's code
{answer}

## Expected outcome
{criterion}

## Evaluation criteria

Grade on these dimensions:
1. **Correctness**: Does the transformation produce the expected output?
2. **Methodology**: Is the data transformation approach sound?
3. **Code quality**: Is the code clean, readable, and well-structured?

If the code is correct and well-written, grade GRADE: C.
If the code is partially correct or has minor issues, grade GRADE: P.
If the code is incorrect or fundamentally flawed, grade GRADE: I.

{instructions}
""",
    "full-project-reproduction": """\
You are evaluating a complete module or project implementation.

## Task
{question}

## Agent's code
{answer}

## Expected outcome
{criterion}

## Evaluation criteria

Grade on these dimensions:
1. **Correctness**: Does the code work as specified?
2. **Architecture**: Is the code well-organized and modular?
3. **Edge cases**: Are edge cases handled appropriately?
4. **Code quality**: Is the code clean, readable, and idiomatic?

If the implementation is correct and well-structured, grade GRADE: C.
If the implementation is partially correct or has structural issues, grade GRADE: P.
If the implementation is incorrect or fundamentally broken, grade GRADE: I.

{instructions}
""",
}


@scorer(metrics=[accuracy(), stderr()])
def judge_scorer(
    archetype: str = "notebook-analysis",
    model: str = "anthropic/claude-opus-4-7",
) -> Scorer:
    """Score by reading agent-produced code from the sandbox and grading it with an LLM.

    Reads .py files from the sandbox, injects them as the 'answer' into
    Inspect's model_graded_qa scorer.
    """

    # Create the inner model_graded_qa scorer
    rubric = RUBRICS.get(archetype, RUBRICS["notebook-analysis"])
    inner_scorer = model_graded_qa(
        template=rubric,
        model=model,
        partial_credit=True,
    )

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
                value="I",
                explanation="No code files found in the sandbox",
            )

        # Inject the code into the state's output so model_graded_qa sees it
        # as the {answer} in the rubric template
        code_text = "\n\n".join(code_parts)
        from inspect_ai.model import ChatMessageAssistant, ModelOutput

        # Save originals, swap in code content, score, then restore
        orig_output = state.output
        orig_messages = list(state.messages)

        state.output = ModelOutput.from_content(
            model="agent", content=code_text
        )
        state.messages.append(ChatMessageAssistant(content=code_text))

        try:
            result = await inner_scorer(state, target)
        finally:
            state.output = orig_output
            state.messages.clear()
            state.messages.extend(orig_messages)

        return result

    return score
