"""Page service implementation."""

import os
import uuid
import aiofiles
from datetime import date
from uuid import UUID
from typing import Any

from fastapi import UploadFile

from app.interfaces.services.page_service import IPageService
from app.interfaces.repositories.page_repository import IPageRepository
from app.core.config import settings


# Allowed image extensions
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


class PageService(IPageService):
    """Service for page business logic."""
    
    def __init__(self, page_repository: IPageRepository):
        """
        Initialize the service with required repositories.
        
        Args:
            page_repository: Repository for page data access
        """
        self.page_repository = page_repository
    
    async def upload_page(
        self,
        user_id: UUID,
        image: UploadFile,
        uploaded_date: date,
        notes: str | None = None
    ) -> dict[str, Any]:
        """Upload a new page image."""
        # Validate file
        if image.filename is None:
            raise ValueError("No image file provided")
        
        # Get file extension
        _, ext = os.path.splitext(image.filename)
        ext = ext.lower()
        
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Invalid image format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
        
        # Check file size (read in chunks to avoid memory issues)
        content = await image.read()
        if len(content) > settings.max_upload_size:
            raise ValueError(f"File too large. Maximum size: {settings.max_upload_size // (1024 * 1024)}MB")
        
        # Reset file position for saving
        await image.seek(0)
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}{ext}"
        
        # Create user's upload directory if it doesn't exist
        user_upload_dir = os.path.join(settings.upload_dir, str(user_id))
        os.makedirs(user_upload_dir, exist_ok=True)
        
        # Full path to save the file
        file_path = os.path.join(user_upload_dir, unique_filename)
        
        # Save the file
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        
        # Store relative path in database
        relative_path = f"{user_id}/{unique_filename}"
        
        # Create page record
        page = await self.page_repository.create(
            user_id=user_id,
            image_path=relative_path,
            uploaded_date=uploaded_date,
            notes=notes
        )
        
        # Transform for API response
        return {
            "id": page["id"],
            "image_url": self.get_image_url(page["image_path"]),
            "uploaded_date": page["uploaded_date"],
            "page_start_date": page["page_start_date"],
            "page_end_date": page["page_end_date"],
            "notes": page["notes"],
            "page_status": page["page_status"],
            "created_at": page["created_at"],
        }
    
    async def get_page(
        self,
        page_id: UUID,
        user_id: UUID
    ) -> dict[str, Any]:
        """Get a page by ID."""
        page = await self.page_repository.get_by_id(page_id, user_id)
        
        if page is None:
            raise ValueError("Page not found")
        
        return {
            "id": page["id"],
            "image_url": self.get_image_url(page["image_path"]),
            "uploaded_date": page["uploaded_date"],
            "page_start_date": page["page_start_date"],
            "page_end_date": page["page_end_date"],
            "notes": page["notes"],
            "page_status": page["page_status"],
            "created_at": page["created_at"],
        }
    
    async def delete_page(
        self,
        page_id: UUID,
        user_id: UUID
    ) -> None:
        """Delete a page and its image file."""
        # Get the image path before deleting
        image_path = await self.page_repository.get_image_path(page_id, user_id)
        
        if image_path is None:
            raise ValueError("Page not found")
        
        # Delete from database (cascades to entries)
        deleted = await self.page_repository.delete(page_id, user_id)
        
        if not deleted:
            raise ValueError("Failed to delete page")
        
        # Delete the image file
        full_path = os.path.join(settings.upload_dir, image_path)
        if os.path.exists(full_path):
            os.remove(full_path)
    
    async def update_page_status(
        self,
        page_id: UUID,
        user_id: UUID,
        page_status: str,
        page_start_date: date | None = None,
        page_end_date: date | None = None
    ) -> dict[str, Any]:
        """Update a page's status (used after transcription)."""
        # Validate status
        if page_status not in ("pending", "transcribed"):
            raise ValueError("Invalid page status")
        
        # Check if page exists
        if not await self.page_repository.exists(page_id, user_id):
            raise ValueError("Page not found")
        
        # Update the page
        page = await self.page_repository.update_status(
            page_id=page_id,
            user_id=user_id,
            page_status=page_status,
            page_start_date=page_start_date,
            page_end_date=page_end_date
        )
        
        if page is None:
            raise ValueError("Failed to update page")
        
        return {
            "id": page["id"],
            "image_url": self.get_image_url(page["image_path"]),
            "uploaded_date": page["uploaded_date"],
            "page_start_date": page["page_start_date"],
            "page_end_date": page["page_end_date"],
            "notes": page["notes"],
            "page_status": page["page_status"],
            "created_at": page["created_at"],
        }
    
    def get_image_url(self, image_path: str) -> str:
        """Construct the full URL for an image path."""
        base_url = f"http://{settings.api_host}:{settings.api_port}"
        return f"{base_url}/uploads/{image_path}"
