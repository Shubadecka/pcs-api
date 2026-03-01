"""Page service implementation."""

import os
import uuid
import logging
import aiofiles
from datetime import date
from uuid import UUID
from typing import Any

from fastapi import UploadFile

from app.interfaces.services.page_service import IPageService
from app.interfaces.repositories.page_repository import IPageRepository
from app.interfaces.repositories.entry_repository import IEntryRepository
from app.core.config import settings
from app.core.ollama_utils import ollama
from app.services.transcription_processing import TranscriptionProcessingService

_transcription_processor = TranscriptionProcessingService()

logger = logging.getLogger("page_service")


# Allowed image extensions
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


class PageService(IPageService):
    """Service for page business logic."""
    
    def __init__(self, page_repository: IPageRepository, entry_repository: IEntryRepository | None = None):
        """
        Initialize the service with required repositories.
        
        Args:
            page_repository: Repository for page data access
            entry_repository: Repository for entry data access (used for auto-transcription)
        """
        self.page_repository = page_repository
        self.entry_repository = entry_repository
    
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

        # Create page record (status: pending)
        page = await self.page_repository.create(
            user_id=user_id,
            image_path=relative_path,
            uploaded_date=uploaded_date,
            notes=notes,
        )

        # Run OCR, split into dated entries, persist each one, then mark page as transcribed
        if self.entry_repository is not None:
            raw_text = await ollama.ocr(file_path)
            if raw_text:
                result = await _transcription_processor.process(raw_text, uploaded_date)
                if result and result.entries:
                    for parsed_entry in result.entries:
                        await self.entry_repository.create(
                            user_id=user_id,
                            page_id=page["id"],
                            entry_date=parsed_entry.entry_date,
                            transcription=parsed_entry.text,
                        )
                    page = await self.page_repository.update_status(
                        page_id=page["id"],
                        user_id=user_id,
                        page_status="transcribed",
                    ) or page
        
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
    
    async def process_page(
        self,
        page_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        """Run OCR and transcription processing on an existing page.

        Clears any existing entries for the page, creates new ones from the
        OCR + processing pipeline, and marks the page as transcribed.

        Returns a dict with keys 'page' and 'entries'.
        Raises ValueError if the page is not found or OCR yields no text.
        """
        if self.entry_repository is None:
            raise ValueError("Entry repository is required for processing")

        page = await self.page_repository.get_by_id(page_id, user_id)
        if page is None:
            raise ValueError("Page not found")

        full_path = os.path.join(settings.upload_dir, page["image_path"])

        raw_text = await ollama.ocr(full_path)
        if not raw_text:
            raise ValueError("OCR returned no text for this page")

        result = await _transcription_processor.process(raw_text, page["uploaded_date"])
        if not result or not result.entries:
            raise ValueError("Transcription processing returned no entries")

        if page["page_status"] == "transcribed":
            logger.warning(
                "Page %s has already been transcribed. "
                "New entries will be appended — delete duplicates manually if needed.",
                page_id,
            )

        created_entries = []
        for parsed_entry in result.entries:
            entry = await self.entry_repository.create(
                user_id=user_id,
                page_id=page_id,
                entry_date=parsed_entry.entry_date,
                transcription=parsed_entry.transcription,
            )
            created_entries.append(entry)

        page = await self.page_repository.update_status(
            page_id=page_id,
            user_id=user_id,
            page_status="transcribed",
        ) or page

        return {
            "page": {
                "id": page["id"],
                "image_url": self.get_image_url(page["image_path"]),
                "uploaded_date": page["uploaded_date"],
                "page_start_date": page["page_start_date"],
                "page_end_date": page["page_end_date"],
                "notes": page["notes"],
                "page_status": page["page_status"],
                "created_at": page["created_at"],
            },
            "entries": created_entries,
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
    
    async def get_all_pages(
        self,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None
    ) -> list[dict[str, Any]]:
        """Get all pages for a user, with optional written-date range filter."""
        pages = await self.page_repository.get_all_by_user(user_id, start_date, end_date)
        return [
            {
                "id": p["id"],
                "image_url": self.get_image_url(p["image_path"]),
                "uploaded_date": p["uploaded_date"],
                "page_start_date": p["page_start_date"],
                "page_end_date": p["page_end_date"],
                "notes": p["notes"],
                "page_status": p["page_status"],
                "created_at": p["created_at"],
            }
            for p in pages
        ]

    def get_image_url(self, image_path: str) -> str:
        """Construct the full URL for an image path."""
        base_url = f"http://{settings.api_host}:{settings.api_port}"
        return f"{base_url}/uploads/{image_path}"
