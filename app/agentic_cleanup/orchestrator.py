"""Agent loop orchestrator for the agentic OCR cleanup layer."""

import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agentic_cleanup.error_detection import detect_errors
from app.agentic_cleanup.tools import (
    AgentAbortError,
    AgentFinishError,
    CleanupTools,
    TOOL_DEFINITIONS,
)
from app.core.config import settings
from app.core.ollama_utils import OllamaClient
from app.interfaces.agentic_cleanup.cleanup_orchestrator import ICleanupOrchestrator
from app.interfaces.repositories.entry_repository import IEntryRepository

logger = logging.getLogger("agentic_cleanup.orchestrator")

_SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.md"


def _load_system_prompt() -> str:
    return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


class CleanupOrchestrator(ICleanupOrchestrator):
    """Drives the tool-calling agent loop that improves OCR transcriptions.

    The orchestrator owns the iteration counter and tool dispatch. It is a
    stateless service — a new instance can be created per request. The DB
    session is passed into improve_entry() rather than stored at construction
    so the orchestrator is straightforward to test with a mock session.
    """

    def __init__(self, entry_repo: IEntryRepository, ollama_client: OllamaClient) -> None:
        self._repo = entry_repo
        self._ollama = ollama_client

    async def improve_entry(
        self,
        entry_id: UUID,
        user_id: UUID,
        db: AsyncSession,
    ) -> None:
        """Run the agent loop to improve the OCR transcription of an entry.

        See ICleanupOrchestrator for full contract documentation.
        """
        # 1. Fetch the target entry (ownership verified by user_id scope)
        entry = await self._repo.get_by_id(entry_id, user_id)
        if entry is None:
            raise ValueError(f"Entry {entry_id} not found for user {user_id}")

        raw_text: str = entry["raw_ocr_transcription"]
        entry_date: str = str(entry["entry_date"])
        logger.info("Starting agent cleanup for entry %s (date=%s)", entry_id, entry_date)

        # 2. Pre-analysis pass: identify suspected errors to seed the agent context
        error_analysis = await detect_errors(raw_text)

        # 3. Build the initial message list
        system_prompt = _load_system_prompt()
        user_message = _build_user_message(entry_date, raw_text, error_analysis)

        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        # 4. Instantiate tools scoped to this user and entry
        tools = CleanupTools(db=db, user_id=user_id, entry_id=entry_id)

        # 5. Agent loop
        max_iter = settings.agent_max_iterations
        for iteration in range(1, max_iter + 1):
            logger.info("Agent loop iteration %d/%d for entry %s", iteration, max_iter, entry_id)

            response_message = await self._ollama.chat(
                messages=messages,
                tools=TOOL_DEFINITIONS,
            )

            if response_message is None:
                logger.warning(
                    "chat() returned None on iteration %d — aborting cleanup for entry %s",
                    iteration,
                    entry_id,
                )
                return

            # Append the assistant's message to keep the conversation coherent
            messages.append(response_message)

            tool_calls = response_message.get("tool_calls")

            if not tool_calls:
                # Model responded with plain text and no tool calls — treat as done
                logger.info(
                    "No tool calls on iteration %d — agent finished without explicit finish/abort",
                    iteration,
                )
                return

            # Dispatch each tool call in sequence
            for call in tool_calls:
                fn = call.get("function", {})
                tool_name: str = fn.get("name", "")
                tool_args: dict = fn.get("arguments", {})

                try:
                    tool_result = await tools.dispatch(tool_name, tool_args)
                except AgentFinishError as exc:
                    await _write_improvement(self._repo, entry_id, user_id, exc.corrected_text)
                    logger.info(
                        "Agent finished successfully for entry %s (%d iterations)",
                        entry_id,
                        iteration,
                    )
                    return
                except AgentAbortError:
                    logger.info(
                        "Agent aborted for entry %s after %d iteration(s) — no changes written",
                        entry_id,
                        iteration,
                    )
                    return

                # Append the tool result as a tool message for the next iteration
                messages.append({
                    "role": "tool",
                    "content": tool_result,
                })

        # Reached max iterations without finish or abort
        logger.warning(
            "Agent reached max iterations (%d) for entry %s — no changes written",
            max_iter,
            entry_id,
        )


async def _write_improvement(
    repo: IEntryRepository,
    entry_id: UUID,
    user_id: UUID,
    corrected_text: str,
) -> None:
    """Persist the agent's corrected text to the database."""
    result = await repo.update(
        entry_id=entry_id,
        user_id=user_id,
        improved_transcription=corrected_text,
        agent_has_improved=True,
    )
    if result is None:
        logger.error(
            "Failed to write improvement for entry %s — update returned None", entry_id
        )


def _build_user_message(entry_date: str, raw_text: str, error_analysis: str) -> str:
    """Compose the initial user message that seeds the agent loop."""
    parts = [
        f"Journal entry date: {entry_date}",
        "",
        "Raw OCR transcription:",
        "---",
        raw_text,
        "---",
    ]

    if error_analysis:
        parts += [
            "",
            "Pre-analysis — suspected OCR errors:",
            "---",
            error_analysis,
            "---",
        ]
    else:
        parts += ["", "No pre-analysis available."]

    parts += [
        "",
        "Please investigate the suspected errors using the available tools and "
        "either submit a corrected transcription with finish() or call abort() if "
        "no reliable corrections can be made.",
    ]

    return "\n".join(parts)
