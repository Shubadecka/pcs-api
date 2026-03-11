"""Vector similarity retrieval for the agentic cleanup layer."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.entry_repository import EntryRepository

logger = logging.getLogger("agentic_cleanup.retrieval")

_PREVIEW_CHARS = 100


async def search_similar_entries(
    db: AsyncSession,
    user_id: UUID,
    query_embedding: list[float],
    limit: int = 3,
    exclude_entry_id: UUID | None = None,
) -> list[dict]:
    """Find journal entries whose embeddings are closest to query_embedding.

    Delegates to EntryRepository.search_similar and returns lightweight
    preview dicts to avoid overwhelming the agent's context window.

    Args:
        db: Active database session
        user_id: Owner UUID — results are scoped to this user only
        query_embedding: The query vector produced by embedding the search text
        limit: Maximum number of results to return (default 3)
        exclude_entry_id: Optional entry to exclude (typically the one being cleaned)

    Returns:
        List of dicts with keys: `id` (str), `entry_date` (str), `preview` (str)
        where `preview` is the first 100 characters of `raw_ocr_transcription`.
    """
    repo = EntryRepository(db)
    rows = await repo.search_similar(
        user_id=user_id,
        query_embedding=query_embedding,
        limit=limit,
        exclude_entry_id=exclude_entry_id,
    )

    results = []
    for row in rows:
        raw = row.get("raw_ocr_transcription") or ""
        results.append({
            "id": str(row["id"]),
            "entry_date": str(row["entry_date"]),
            "preview": raw[:_PREVIEW_CHARS],
        })

    logger.debug(
        "search_similar_entries returned %d results for user %s", len(results), user_id
    )
    return results
