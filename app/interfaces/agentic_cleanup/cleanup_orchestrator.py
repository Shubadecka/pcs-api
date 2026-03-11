"""Interface for the agentic cleanup orchestrator."""

from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class ICleanupOrchestrator(ABC):
    """Abstract base class for the agentic OCR cleanup orchestrator."""

    @abstractmethod
    async def improve_entry(
        self,
        entry_id: UUID,
        user_id: UUID,
        db: AsyncSession,
    ) -> None:
        """Run the agent loop to improve the OCR transcription of an entry.

        Fetches the entry, runs a pre-analysis pass to identify likely OCR
        errors, then drives a tool-calling agent loop that uses RAG over
        existing journal entries to produce a corrected transcription.

        On success, writes the corrected text to `improved_transcription` and
        sets `agent_has_improved = True`. On failure or explicit abort, no
        database writes are made.

        Args:
            entry_id: UUID of the entry to improve
            user_id: UUID of the owning user (used to scope all DB access)
            db: An open AsyncSession owned by the caller (background task)

        Raises:
            ValueError: If the entry does not exist or is not owned by user_id
        """
        ...
