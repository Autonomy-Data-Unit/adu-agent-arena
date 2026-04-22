"""LLM-judge scorer templates for each test archetype."""

from inspect_ai.scorer import Scorer, model_graded_qa

PIPELINE_STAGE_RUBRIC = """\
You are evaluating code that performs a data pipeline transformation.

## Task
{question}

## Agent's output
{answer}

## Expected approach
{criterion}

## Evaluation criteria

Grade the output on these dimensions:
1. **Correctness**: Does the code produce the expected output when run?
2. **Methodology**: Is the data transformation approach sound and appropriate?
3. **Code quality**: Is the code clean, readable, and well-structured?

If the code is correct and the methodology is sound, grade GRADE: C.
If the code is partially correct or has minor issues, grade GRADE: P.
If the code is incorrect or the methodology is fundamentally flawed, grade GRADE: I.

{instructions}
"""

SCRAPE_AND_STRUCTURE_RUBRIC = """\
You are evaluating code that scrapes and structures data from web sources.

## Task
{question}

## Agent's output
{answer}

## Expected approach
{criterion}

## Evaluation criteria

Grade the output on these dimensions:
1. **Correctness**: Does the scraper extract the right data?
2. **Robustness**: Does it handle edge cases (missing fields, malformed HTML)?
3. **Structure**: Is the output data well-structured and validated?
4. **Code quality**: Is the code clean and readable?

If the code is correct and robust, grade GRADE: C.
If the code is partially correct or fragile, grade GRADE: P.
If the code fails to extract data correctly, grade GRADE: I.

{instructions}
"""

NOTEBOOK_ANALYSIS_RUBRIC = """\
You are evaluating a data analysis notebook or script.

## Task
{question}

## Agent's output
{answer}

## Expected approach
{criterion}

## Evaluation criteria

Grade the output on these dimensions:
1. **Correctness**: Are the numerical results correct?
2. **Methodology**: Is the analytical approach sound and appropriate?
3. **Completeness**: Does it address all parts of the task?
4. **Clarity**: Are the results clearly presented?

If the analysis is correct and complete, grade GRADE: C.
If the analysis is partially correct or incomplete, grade GRADE: P.
If the analysis is incorrect or fundamentally flawed, grade GRADE: I.

{instructions}
"""

FULL_PROJECT_RUBRIC = """\
You are evaluating a complete module or project implementation.

## Task
{question}

## Agent's output
{answer}

## Expected approach
{criterion}

## Evaluation criteria

Grade the output on these dimensions:
1. **Correctness**: Does the code work as specified?
2. **Architecture**: Is the code well-organized and modular?
3. **Edge cases**: Are edge cases handled appropriately?
4. **Code quality**: Is the code clean, readable, and idiomatic?

If the implementation is correct and well-structured, grade GRADE: C.
If the implementation is partially correct or has structural issues, grade GRADE: P.
If the implementation is incorrect or fundamentally broken, grade GRADE: I.

{instructions}
"""

RUBRICS = {
    "pipeline-stage": PIPELINE_STAGE_RUBRIC,
    "scrape-and-structure": SCRAPE_AND_STRUCTURE_RUBRIC,
    "notebook-analysis": NOTEBOOK_ANALYSIS_RUBRIC,
    "full-project-reproduction": FULL_PROJECT_RUBRIC,
}


def judge_scorer(
    archetype: str,
    model: str = "openai/gpt-4o",
) -> Scorer:
    """Create an LLM-judge scorer for a given test archetype."""
    rubric = RUBRICS[archetype]
    return model_graded_qa(
        template=rubric,
        model=model,
        partial_credit=True,
        include_history=True,
    )
