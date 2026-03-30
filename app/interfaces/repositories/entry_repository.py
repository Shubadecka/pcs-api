"""Interface for entry repository."""

from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID
from typing import Any


class IEntryRepository(ABC):
    """Abstract base class for entry data access operations."""
    
    @abstractmethod
    async def get_all(
        self,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        limit: int = 50
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Get all entries for a user with optional filtering.
        
        Args:
            user_id: The user's UUID
            start_date: Optional start date filter (inclusive)
            end_date: Optional end date filter (inclusive)
            page: Page number (1-indexed)
            limit: Number of items per page
            
        Returns:
            Tuple of (list of entries, total count)
        """
        ...
    
    @abstractmethod
    async def get_by_id(
        self,
        entry_id: UUID,
        user_id: UUID
    ) -> dict[str, Any] | None:
        """
        Get an entry by ID for a specific user.
        
        Args:
            entry_id: The entry's UUID
            user_id: The user's UUID (for ownership check)
            
        Returns:
            The entry record if found and owned by user, None otherwise
        """
        ...
    
    @abstractmethod
    async def create(
        self,
        user_id: UUID,
        page_id: UUID,
        entry_date: date,
        raw_ocr_transcription: str,
        embedding: list[float] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new entry.
        
        Args:
            user_id: The user's UUID
            page_id: The associated page's UUID
            entry_date: The journal entry date
            raw_ocr_transcription: The raw OCR transcribed text
            embedding: Optional vector embedding of the transcription
            
        Returns:
            The created entry record
        """
        ...
    
    @abstractmethod
    async def update(
        self,
        entry_id: UUID,
        user_id: UUID,
        entry_date: date | None = None,
        improved_transcription: str | None = None,
        agent_has_improved: bool | None = None,
    ) -> dict[str, Any] | None:
        """
        Update an entry.

        `raw_ocr_transcription` is intentionally excluded — it is immutable
        after creation. `agent_has_improved` should only be set by the agentic
        cleanup pipeline, not by user-facing service calls.

        Args:
            entry_id: The entry's UUID
            user_id: The user's UUID (for ownership check)
            entry_date: Optional new entry date
            improved_transcription: Optional improved transcription text
            agent_has_improved: Optional flag set by the agentic cleanup pipeline

        Returns:
            The updated entry record if found and owned by user, None otherwise
        """
        ...
    
    @abstractmethod
    async def delete(self, entry_id: UUID, user_id: UUID) -> bool:
        """
        Delete an entry.
        
        Args:
            entry_id: The entry's UUID
            user_id: The user's UUID (for ownership check)
            
        Returns:
            True if deleted, False if not found or not owned by user
        """
        ...
    
    @abstractmethod
    async def exists(self, entry_id: UUID, user_id: UUID) -> bool:
        """
        Check if an entry exists and is owned by the user.
        
        Args:
            entry_id: The entry's UUID
            user_id: The user's UUID
            
        Returns:
            True if exists and owned by user, False otherwise
        """
        ...

    @abstractmethod
    async def search_similar(
        self,
        user_id: UUID,
        query_embedding: list[float],
        limit: int = 3,
        exclude_entry_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Find entries whose embeddings are closest to query_embedding.

        Args:
            user_id: The user's UUID (ownership scoping)
            query_embedding: The query vector to compare against
            limit: Maximum number of results to return
            exclude_entry_id: Optional entry UUID to exclude from results
                (used to avoid returning the entry being cleaned)

        Returns:
            List of entry records ordered by cosine similarity (most similar first)
        """
        ...

    @abstractmethod
    async def delete_by_page_id(self, page_id: UUID, user_id: UUID) -> int:
        """
        Delete all entries belonging to a page.

        Args:
            page_id: The page's UUID
            user_id: The user's UUID (ownership check on the parent page)

        Returns:
            Number of entries deleted
        """
        ...
