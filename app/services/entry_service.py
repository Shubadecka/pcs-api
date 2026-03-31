"""Entry service implementation."""

from datetime import date
from uuid import UUID
from typing import Any

from app.interfaces.services.entry_service import IEntryService
from app.interfaces.repositories.entry_repository import IEntryRepository


class EntryService(IEntryService):
    """Service for entry business logic."""
    
    def __init__(self, entry_repository: IEntryRepository):
        """
        Initialize the service with required repositories.
        
        Args:
            entry_repository: Repository for entry data access
        """
        self.entry_repository = entry_repository
    
    async def get_entries(
        self,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        limit: int = 50,
        sort_by: str = "entry_date",
        filter_field: str = "entry_date",
        page_id: UUID | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Get all entries for a user with optional filtering."""
        if page < 1:
            page = 1
        if limit < 1:
            limit = 1
        if limit > 100:
            limit = 100

        entries, total = await self.entry_repository.get_all(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            page=page,
            limit=limit,
            sort_by=sort_by,
            filter_field=filter_field,
            page_id=page_id,
        )
        
        # Transform entries for API response
        transformed_entries = []
        for entry in entries:
            transformed_entries.append({
                "id": entry["id"],
                "entry_date": entry["entry_date"],
                "raw_ocr_transcription": entry["raw_ocr_transcription"],
                "improved_transcription": entry["improved_transcription"],
                "agent_has_improved": entry["agent_has_improved"],
                "page_id": entry["page_id"],
                "created_at": entry["created_at"],
                "updated_at": entry["updated_at"],
                "status": "transcribed",  # Entries only exist after transcription
            })
        
        return transformed_entries, total
    
    async def get_entry(
        self,
        entry_id: UUID,
        user_id: UUID
    ) -> dict[str, Any]:
        """Get a single entry by ID."""
        entry = await self.entry_repository.get_by_id(entry_id, user_id)
        
        if entry is None:
            raise ValueError("Entry not found")
        
        return {
            "id": entry["id"],
            "entry_date": entry["entry_date"],
            "raw_ocr_transcription": entry["raw_ocr_transcription"],
            "improved_transcription": entry["improved_transcription"],
            "agent_has_improved": entry["agent_has_improved"],
            "page_id": entry["page_id"],
            "created_at": entry["created_at"],
            "updated_at": entry["updated_at"],
            "status": "transcribed",
        }
    
    async def update_entry(
        self,
        entry_id: UUID,
        user_id: UUID,
        entry_date: date | None = None,
        improved_transcription: str | None = None,
    ) -> dict[str, Any]:
        """Update an entry's user-editable fields."""
        # Check if entry exists and is owned by user
        if not await self.entry_repository.exists(entry_id, user_id):
            raise ValueError("Entry not found")

        # Update the entry
        entry = await self.entry_repository.update(
            entry_id=entry_id,
            user_id=user_id,
            entry_date=entry_date,
            improved_transcription=improved_transcription,
        )
        
        if entry is None:
            raise ValueError("Failed to update entry")
        
        return {
            "id": entry["id"],
            "entry_date": entry["entry_date"],
            "raw_ocr_transcription": entry["raw_ocr_transcription"],
            "improved_transcription": entry["improved_transcription"],
            "agent_has_improved": entry["agent_has_improved"],
            "page_id": entry["page_id"],
            "created_at": entry["created_at"],
            "updated_at": entry["updated_at"],
            "status": "transcribed",
        }
    
    async def delete_entry(
        self,
        entry_id: UUID,
        user_id: UUID
    ) -> None:
        """Delete an entry."""
        # Check if entry exists and is owned by user
        if not await self.entry_repository.exists(entry_id, user_id):
            raise ValueError("Entry not found")
        
        # Delete the entry
        deleted = await self.entry_repository.delete(entry_id, user_id)
        
        if not deleted:
            raise ValueError("Failed to delete entry")
