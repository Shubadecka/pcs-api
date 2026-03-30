"""Tool definitions and implementations for the agentic cleanup agent."""

import json
import logging
from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agentic_cleanup.retrieval import search_similar_entries
from app.core.ollama_utils import ollama
from app.repositories.entry_repository import EntryRepository

logger = logging.getLogger("agentic_cleanup.tools")


class AgentAbortError(Exception):
    """Raised by CleanupTools.abort() to signal a clean exit without DB writes."""


class AgentFinishError(Exception):
    """Raised by CleanupTools.finish() to signal successful completion.

    The corrected text is stored on the exception so the orchestrator can
    retrieve it after catching.
    """

    def __init__(self, corrected_text: str) -> None:
        super().__init__()
        self.corrected_text = corrected_text


class CleanupTools:
    """Agent tool implementations, scoped to a single user and DB session.

    Constructed once per agent run. The user_id is baked in at construction
    time so every database call is automatically scoped — the agent cannot
    access another user's data regardless of what arguments it passes.
    """

    def __init__(self, db: AsyncSession, user_id: UUID, entry_id: UUID) -> None:
        self._db = db
        self._user_id = user_id
        self._entry_id = entry_id
        self._repo = EntryRepository(db)

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    async def search_similar_entries(self, query: str) -> list[dict]:
        """Embed query and return the 3 most similar entries (id + preview).

        Args:
            query: A phrase from the entry being cleaned to use as the search query

        Returns:
            List of dicts with keys: id, entry_date, preview (first 100 chars)
        """
        query_embedding = await ollama.embed(query)
        if not query_embedding:
            logger.warning("search_similar_entries: embedding failed, returning empty list")
            return []

        return await search_similar_entries(
            db=self._db,
            user_id=self._user_id,
            query_embedding=query_embedding,
            limit=3,
            exclude_entry_id=self._entry_id,
        )

    async def get_entry_by_id(self, entry_id: str) -> dict | None:
        """Fetch the full text of an entry by its UUID string.

        Args:
            entry_id: UUID string of the entry to retrieve

        Returns:
            Entry dict with id, entry_date, raw_ocr_transcription,
            improved_transcription, or None if not found / not owned by user.
        """
        try:
            uid = UUID(entry_id)
        except ValueError:
            logger.warning("get_entry_by_id: invalid UUID '%s'", entry_id)
            return None

        row = await self._repo.get_by_id(uid, self._user_id)
        if row is None:
            return None

        return {
            "id": str(row["id"]),
            "entry_date": str(row["entry_date"]),
            "raw_ocr_transcription": row["raw_ocr_transcription"],
            "improved_transcription": row.get("improved_transcription"),
        }

    async def get_entries_by_date_range(
        self, start_date: str, end_date: str
    ) -> list[dict]:
        """Retrieve entries within a date range (YYYY-MM-DD format).

        Args:
            start_date: Inclusive start date string in YYYY-MM-DD format
            end_date: Inclusive end date string in YYYY-MM-DD format

        Returns:
            List of entry dicts with id, entry_date, raw_ocr_transcription,
            improved_transcription.
        """
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except ValueError as exc:
            logger.warning("get_entries_by_date_range: invalid date — %s", exc)
            return []

        rows, _ = await self._repo.get_all(
            user_id=self._user_id,
            start_date=start,
            end_date=end,
            page=1,
            limit=10,
        )

        return [
            {
                "id": str(row["id"]),
                "entry_date": str(row["entry_date"]),
                "raw_ocr_transcription": row["raw_ocr_transcription"],
                "improved_transcription": row.get("improved_transcription"),
            }
            for row in rows
        ]

    async def finish(self, corrected_text: str) -> None:
        """Signal successful completion with the corrected transcription.

        Raises AgentFinishError, which the orchestrator catches to write the
        corrected text to the database.

        Args:
            corrected_text: The full corrected journal entry text
        """
        raise AgentFinishError(corrected_text)

    async def abort(self) -> None:
        """Signal a clean exit without making any database changes.

        Raises AgentAbortError, which the orchestrator catches to exit the
        loop without writing to the database.
        """
        raise AgentAbortError()

    # ------------------------------------------------------------------
    # Tool dispatch
    # ------------------------------------------------------------------

    async def dispatch(self, name: str, arguments: dict) -> str:
        """Dispatch a tool call by name and return the result as a JSON string.

        Args:
            name: Tool name as provided by the model
            arguments: Parsed argument dict from the model's tool_call

        Returns:
            JSON-encoded result string to append as a tool message.

        Raises:
            AgentFinishError: When finish() is called
            AgentAbortError: When abort() is called
        """
        logger.info("Tool call: %s(%s)", name, arguments)

        if name == "search_similar_entries":
            result = await self.search_similar_entries(arguments.get("query", ""))
        elif name == "get_entry_by_id":
            result = await self.get_entry_by_id(arguments.get("entry_id", ""))
        elif name == "get_entries_by_date_range":
            result = await self.get_entries_by_date_range(
                arguments.get("start_date", ""),
                arguments.get("end_date", ""),
            )
        elif name == "finish":
            await self.finish(arguments.get("corrected_text", ""))
        elif name == "abort":
            await self.abort()
        else:
            logger.warning("Unknown tool called: %s", name)
            result = {"error": f"Unknown tool: {name}"}

        return json.dumps(result)


# ------------------------------------------------------------------
# Tool JSON schema definitions (Ollama /api/chat format)
# ------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_similar_entries",
            "description": (
                "Search for journal entries similar to a query phrase using vector similarity. "
                "Returns up to 3 results with entry id, date, and a short preview (first 100 chars). "
                "Use get_entry_by_id to fetch the full text of a promising result."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A representative phrase from the entry being cleaned",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_entry_by_id",
            "description": (
                "Retrieve the full text of a journal entry by its UUID. "
                "Use after search_similar_entries to read complete entries."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entry_id": {
                        "type": "string",
                        "description": "UUID string of the entry to retrieve",
                    }
                },
                "required": ["entry_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_entries_by_date_range",
            "description": (
                "Retrieve journal entries within a date range. "
                "Useful for finding entries close in time to the one being cleaned."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Inclusive start date in YYYY-MM-DD format",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Inclusive end date in YYYY-MM-DD format",
                    },
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": (
                "Submit the corrected transcription and end the agent loop. "
                "Call this when you are confident you have a better version than the original. "
                "Pass the complete corrected entry text, not just the changed portions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "corrected_text": {
                        "type": "string",
                        "description": "The full corrected journal entry text",
                    }
                },
                "required": ["corrected_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "abort",
            "description": (
                "Exit the agent loop without making any changes. "
                "Call this when no OCR errors are found, or when you cannot determine "
                "corrections with sufficient confidence."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]
