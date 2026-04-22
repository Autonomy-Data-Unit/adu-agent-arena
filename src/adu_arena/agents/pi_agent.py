"""Pi-coding-agent solver for Inspect AI."""

import json
import os
from pathlib import Path

from inspect_ai.solver import Solver, TaskState, Generate, solver
from inspect_ai.model import ModelOutput, ChatMessageAssistant
from inspect_ai.util import sandbox

API_KEY_ENV_VARS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GEMINI_API_KEY",
}

SESSIONS_DIR = Path("sessions")


@solver
def pi_coding_agent(
    timeout: int = 900,
    tools: str = "read,bash,edit,write",
    thinking: str = "medium",
) -> Solver:
    """Run pi-coding-agent inside the sandbox container.

    Uses --mode json for structured JSONL output with full tool-call
    visibility. The complete session is saved to sessions/<eval_id>.jsonl.
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
                "--mode",
                "json",
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

        # Parse the JSONL output to extract the final assistant message
        # and save the full session
        raw_output = result.stdout or ""
        assistant_text = ""
        session_events: list[dict] = []

        for line in raw_output.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                session_events.append(event)

                # Extract assistant text from agent_end event
                if event.get("type") == "agent_end":
                    for msg in event.get("messages", []):
                        if msg.get("role") == "assistant":
                            for part in msg.get("content", []):
                                if isinstance(part, dict) and part.get("type") == "text":
                                    assistant_text += part.get("text", "")
                                elif isinstance(part, str):
                                    assistant_text += part
            except json.JSONDecodeError:
                # Non-JSON lines (e.g. stderr leaking to stdout)
                continue

        if not assistant_text and result.success:
            # Fallback: use raw output if no structured events parsed
            assistant_text = raw_output
        elif not result.success:
            assistant_text = f"ERROR (exit {result.returncode}): {result.stderr}"

        # Save full session to disk
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        task_name = state.metadata.get("archetype", "unknown")
        sample_id = state.sample_id or "0"
        session_file = SESSIONS_DIR / f"{provider}_{model}_{task_name}_{sample_id}.jsonl"
        with open(session_file, "w") as f:
            for event in session_events:
                f.write(json.dumps(event) + "\n")

        state.messages.append(ChatMessageAssistant(content=assistant_text))
        state.output = ModelOutput.from_content(
            model=f"pi/{provider}/{model}", content=assistant_text
        )

        return state

    return solve
