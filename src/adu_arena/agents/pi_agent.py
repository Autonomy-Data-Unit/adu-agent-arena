"""Pi-coding-agent solver for Inspect AI."""

import os

from inspect_ai.solver import Solver, TaskState, Generate, solver
from inspect_ai.model import ModelOutput, ChatMessageAssistant
from inspect_ai.util import sandbox

# Map Inspect model strings to pi provider/model
PI_PROVIDER_MAP = {
    "openai": "openai",
    "anthropic": "anthropic",
    "google": "google",
}

API_KEY_ENV_VARS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GEMINI_API_KEY",
}


@solver
def pi_coding_agent(
    timeout: int = 900,
    tools: str = "read,bash,edit,write",
    thinking: str = "medium",
) -> Solver:
    """Run pi-coding-agent inside the sandbox container.

    The provider/model are read from the Inspect model config
    (passed via --model to inspect eval).
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        prompt = state.input_text

        # Extract provider/model from the Inspect model config
        model_name = str(state.model)
        if "/" in model_name:
            provider, model = model_name.split("/", 1)
        else:
            provider, model = "openai", model_name

        # Pass API key into the container
        env: dict[str, str] = {}
        env_var = API_KEY_ENV_VARS.get(provider)
        if env_var:
            key = os.environ.get(env_var, "")
            if key:
                env[env_var] = key

        result = await sandbox().exec(
            cmd=[
                "pi",
                "-p",
                "--no-session",
                "--no-extensions",
                "--no-skills",
                "--no-context-files",
                "--no-prompt-templates",
                "--provider",
                provider,
                "--model",
                model,
                "--thinking",
                thinking,
                "--tools",
                tools,
                prompt,
            ],
            env=env,
            timeout=timeout,
        )

        output_text = result.stdout if result.success else f"ERROR (exit {result.returncode}): {result.stderr}"
        state.messages.append(ChatMessageAssistant(content=output_text))
        state.output = ModelOutput.from_content(model=f"pi/{provider}/{model}", content=output_text)

        return state

    return solve
