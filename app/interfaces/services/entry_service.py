"""Interface for entry service."""

from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID
from typing import Any


class IEntryService(ABC):
    """Abstract base class for entry business logic operations."""
    
    @abstractmethod
    async def get_entries(
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
    async def get_entry(
        self,
        entry_id: UUID,
        user_id: UUID
    ) -> dict[str, Any]:
        """
        Get a single entry by ID.
        
        Args:
            entry_id: The entry's UUID
            user_id: The user's UUID
            
        Returns:
            The entry record
            
        Raises:
            ValueError: If entry not found or not owned by user
        """
        ...
    
    @abstractmethod
    async def update_entry(
        self,
        entry_id: UUID,
        user_id: UUID,
        entry_date: date | None = None,
        improved_transcription: str | None = None,
    ) -> dict[str, Any]:
        """
        Update an entry's user-editable fields.

        `raw_ocr_transcription` is immutable after creation.
        `agent_has_improved` is managed exclusively by the agentic cleanup pipeline.

        Args:
            entry_id: The entry's UUID
            user_id: The user's UUID
            entry_date: Optional new entry date
            improved_transcription: Optional user-edited transcription text

        Returns:
            The updated entry record

        Raises:
            ValueError: If entry not found or not owned by user
        """
        ...
    
    @abstractmethod
    async def delete_entry(
        self,
        entry_id: UUID,
        user_id: UUID
    ) -> None:
        """
        Delete an entry.
        
        Args:
            entry_id: The entry's UUID
            user_id: The user's UUID
            
        Raises:
            ValueError: If entry not found or not owned by user
        """
        ...
