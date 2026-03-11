"""Route handlers for the agentic OCR cleanup endpoint."""

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.agentic_cleanup.orchestrator import CleanupOrchestrator
from app.core.database import create_db_session
from app.core.dependencies import CurrentUserId, DbSession
from app.core.ollama_utils import ollama
from app.repositories.entry_repository import EntryRepository

logger = logging.getLogger("api.cleanup")

router = APIRouter(prefix="/entries", tags=["Cleanup"])


def _get_entry_repo(db: DbSession) -> EntryRepository:
    return EntryRepository(db)


@router.post(
    "/{entry_id}/improve",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger agentic OCR cleanup for an entry",
    responses={
        202: {"description": "Cleanup task accepted and running in the background"},
        401: {"description": "Not authenticated"},
        404: {"description": "Entry not found or not owned by current user"},
    },
)
async def improve_entry(
    entry_id: UUID,
    user_id: CurrentUserId,
    background_tasks: BackgroundTasks,
    db: DbSession,
) -> None:
    """Queue an agentic cleanup run for a single journal entry.

    Returns 202 immediately. The agent runs in the background: on success it
    writes the corrected text to `improved_transcription` and sets
    `agent_has_improved = true`. On failure or abort, no database changes are
    made. Poll `GET /api/entries/{entry_id}` to check `agent_has_improved`.
    """
    entry_repo = _get_entry_repo(db)

    if not await entry_repo.exists(entry_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Entry not found"},
        )

    background_tasks.add_task(_run_cleanup, entry_id, user_id)


async def _run_cleanup(entry_id: UUID, user_id: UUID) -> None:
    """Background task that creates its own DB session and drives the agent loop."""
    async with create_db_session() as db:
        try:
            entry_repo = EntryRepository(db)
            orchestrator = CleanupOrchestrator(entry_repo, ollama)
            await orchestrator.improve_entry(entry_id, user_id, db)
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Agent cleanup failed for entry %s", entry_id)
