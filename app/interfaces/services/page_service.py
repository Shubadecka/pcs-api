"""Interface for page service."""

from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID
from typing import Any

from fastapi import UploadFile


class IPageService(ABC):
    """Abstract base class for page business logic operations."""
    
    @abstractmethod
    async def upload_page(
        self,
        user_id: UUID,
        image: UploadFile,
        uploaded_date: date,
        notes: str | None = None
    ) -> dict[str, Any]:
        """
        Upload a new page image.
        
        Args:
            user_id: The user's UUID
            image: The uploaded image file
            uploaded_date: The date of upload
            notes: Optional notes about the page
            
        Returns:
            The created page record
            
        Raises:
            ValueError: If image format is invalid or file too large
        """
        ...
    
    @abstractmethod
    async def process_page(
        self,
        page_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        """
        Run OCR and transcription processing on an existing page.

        Args:
            page_id: The page's UUID
            user_id: The user's UUID

        Returns:
            Dict with keys 'page' (page record) and 'entries' (list of created entry records)

        Raises:
            ValueError: If page not found, OCR yields nothing, or processing yields no entries
        """
        ...

    @abstractmethod
    async def get_page(
        self,
        page_id: UUID,
        user_id: UUID
    ) -> dict[str, Any]:
        """
        Get a page by ID.
        
        Args:
            page_id: The page's UUID
            user_id: The user's UUID
            
        Returns:
            The page record with full image URL
            
        Raises:
            ValueError: If page not found or not owned by user
        """
        ...
    
    @abstractmethod
    async def delete_page(
        self,
        page_id: UUID,
        user_id: UUID
    ) -> None:
        """
        Delete a page and its image file.
        
        Args:
            page_id: The page's UUID
            user_id: The user's UUID
            
        Raises:
            ValueError: If page not found or not owned by user
        """
        ...
    
    @abstractmethod
    async def update_page_status(
        self,
        page_id: UUID,
        user_id: UUID,
        page_status: str,
        page_start_date: date | None = None,
        page_end_date: date | None = None
    ) -> dict[str, Any]:
        """
        Update a page's status (used after transcription).
        
        Args:
            page_id: The page's UUID
            user_id: The user's UUID
            page_status: New status ('pending' or 'transcribed')
            page_start_date: Optional first journal date on page
            page_end_date: Optional last journal date on page
            
        Returns:
            The updated page record
            
        Raises:
            ValueError: If page not found or not owned by user
        """
        ...
    
    @abstractmethod
    async def get_all_pages(
        self,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None
    ) -> list[dict[str, Any]]:
        """
        Get all pages for a user, optionally filtered by written date range.

        Args:
            user_id: The user's UUID
            start_date: Optional filter start date (written date)
            end_date: Optional filter end date (written date)

        Returns:
            List of page records with full image URLs
        """
        ...

    @abstractmethod
    async def update_page(
        self,
        page_id: UUID,
        user_id: UUID,
        page_start_date: date | None = None,
    ) -> dict[str, Any]:
        """
        Update a page's start date.

        Args:
            page_id: The page's UUID
            user_id: The user's UUID
            page_start_date: The new start date (or None to clear it)

        Returns:
            The updated page record

        Raises:
            ValueError: If page not found or not owned by user
        """
        ...

    @abstractmethod
    def get_image_url(self, image_path: str) -> str:
        """
        Construct the full URL for an image path.
        
        Args:
            image_path: The relative image path
            
        Returns:
            The full URL to the image
        """
        ...
