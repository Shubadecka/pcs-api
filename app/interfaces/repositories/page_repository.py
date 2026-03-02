"""Interface for page repository."""

from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID
from typing import Any


class IPageRepository(ABC):
    """Abstract base class for page data access operations."""
    
    @abstractmethod
    async def create(
        self,
        user_id: UUID,
        image_path: str,
        uploaded_date: date,
        notes: str | None = None
    ) -> dict[str, Any]:
        """
        Create a new page record.
        
        Args:
            user_id: The user's UUID
            image_path: Path to the stored image file
            uploaded_date: The date the page was uploaded
            notes: Optional notes about the page
            
        Returns:
            The created page record
        """
        ...
    
    @abstractmethod
    async def get_by_id(
        self,
        page_id: UUID,
        user_id: UUID
    ) -> dict[str, Any] | None:
        """
        Get a page by ID for a specific user.
        
        Args:
            page_id: The page's UUID
            user_id: The user's UUID (for ownership check)
            
        Returns:
            The page record if found and owned by user, None otherwise
        """
        ...
    
    @abstractmethod
    async def update_status(
        self,
        page_id: UUID,
        user_id: UUID,
        page_status: str,
        page_start_date: date | None = None,
        page_end_date: date | None = None
    ) -> dict[str, Any] | None:
        """
        Update a page's status and date range.
        
        Args:
            page_id: The page's UUID
            user_id: The user's UUID (for ownership check)
            page_status: New status ('pending' or 'transcribed')
            page_start_date: Optional first journal date on page
            page_end_date: Optional last journal date on page
            
        Returns:
            The updated page record if found and owned by user, None otherwise
        """
        ...
    
    @abstractmethod
    async def delete(self, page_id: UUID, user_id: UUID) -> bool:
        """
        Delete a page.
        
        Args:
            page_id: The page's UUID
            user_id: The user's UUID (for ownership check)
            
        Returns:
            True if deleted, False if not found or not owned by user
        """
        ...
    
    @abstractmethod
    async def exists(self, page_id: UUID, user_id: UUID) -> bool:
        """
        Check if a page exists and is owned by the user.
        
        Args:
            page_id: The page's UUID
            user_id: The user's UUID
            
        Returns:
            True if exists and owned by user, False otherwise
        """
        ...
    
    @abstractmethod
    async def get_all_by_user(
        self,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None
    ) -> list[dict[str, Any]]:
        """
        Get all pages owned by a user, optionally filtered by written date range.

        Args:
            user_id: The user's UUID
            start_date: If provided (with end_date), only return pages whose written
                        date range overlaps with [start_date, end_date]
            end_date: See start_date

        Returns:
            List of page records ordered by uploaded_date descending
        """
        ...

    @abstractmethod
    async def update_dates(
        self,
        page_id: UUID,
        user_id: UUID,
        page_start_date: date | None = None,
    ) -> dict[str, Any] | None:
        """
        Update a page's start date without changing status or end date.

        Args:
            page_id: The page's UUID
            user_id: The user's UUID (for ownership check)
            page_start_date: The new start date to set (or None to clear it)

        Returns:
            The updated page record if found and owned by user, None otherwise
        """
        ...

    @abstractmethod
    async def get_image_path(self, page_id: UUID, user_id: UUID) -> str | None:
        """
        Get the image path for a page.
        
        Args:
            page_id: The page's UUID
            user_id: The user's UUID (for ownership check)
            
        Returns:
            The image path if found and owned by user, None otherwise
        """
        ...
