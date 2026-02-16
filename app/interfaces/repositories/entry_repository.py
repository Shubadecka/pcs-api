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
        transcription: str
    ) -> dict[str, Any]:
        """
        Create a new entry.
        
        Args:
            user_id: The user's UUID
            page_id: The associated page's UUID
            entry_date: The journal entry date
            transcription: The transcribed text
            
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
        transcription: str | None = None
    ) -> dict[str, Any] | None:
        """
        Update an entry.
        
        Args:
            entry_id: The entry's UUID
            user_id: The user's UUID (for ownership check)
            entry_date: Optional new entry date
            transcription: Optional new transcription
            
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
