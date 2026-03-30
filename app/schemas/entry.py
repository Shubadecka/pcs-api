"""Entry-related Pydantic schemas."""

from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class EntryResponse(BaseModel):
    """Schema for entry data in responses."""
    
    id: UUID = Field(..., description="Entry's unique identifier")
    entry_date: date = Field(..., alias="date", description="Journal entry date")
    raw_ocr_transcription: str = Field(..., description="Raw OCR transcribed text")
    improved_transcription: str | None = Field(None, description="Agent-improved transcription")
    agent_has_improved: bool = Field(..., description="Whether the agent has improved the transcription")
    page_id: UUID = Field(..., description="Associated page ID")
    created_at: datetime = Field(..., alias="createdAt", description="Entry creation timestamp")
    updated_at: datetime = Field(..., alias="updatedAt", description="Last modification timestamp")
    
    # Include status for API compatibility - derived from page status
    status: str = Field(default="transcribed", description="Entry status (always 'transcribed' since entries only exist after transcription)")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "date": "2024-01-15",
                "raw_ocr_transcription": "Today was a wonderful day...",
                "improved_transcription": None,
                "agent_has_improved": False,
                "status": "transcribed",
                "page_id": "456e4567-e89b-12d3-a456-426614174000",
                "createdAt": "2024-01-15T12:00:00Z",
                "updatedAt": "2024-01-15T14:30:00Z"
            }
        }
    )


class EntryUpdate(BaseModel):
    """Schema for entry update request.

    Only user-editable fields are exposed. `raw_ocr_transcription` is
    immutable after creation and `agent_has_improved` is managed exclusively
    by the agentic cleanup pipeline — neither can be set via this endpoint.
    """

    entry_date: date | None = Field(None, alias="date", description="New journal entry date")
    improved_transcription: str | None = Field(None, description="User-edited transcription text")

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "date": "2024-01-16",
                "improved_transcription": "Updated transcription text..."
            }
        }
    )


class EntryListResponse(BaseModel):
    """Schema for paginated entry list response."""
    
    entries: list[EntryResponse] = Field(..., description="List of entries")
    total: int = Field(..., description="Total number of entries matching the query")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entries": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "date": "2024-01-15",
                        "raw_ocr_transcription": "Today was a wonderful day...",
                        "improved_transcription": None,
                        "agent_has_improved": False,
                        "status": "transcribed",
                        "page_id": "456e4567-e89b-12d3-a456-426614174000",
                        "createdAt": "2024-01-15T12:00:00Z",
                        "updatedAt": "2024-01-15T14:30:00Z"
                    }
                ],
                "total": 1
            }
        }
    )


class SingleEntryResponse(BaseModel):
    """Schema for single entry response wrapper."""
    
    entry: EntryResponse = Field(..., description="The entry data")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entry": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "date": "2024-01-15",
                    "raw_ocr_transcription": "Today was a wonderful day...",
                    "improved_transcription": None,
                    "agent_has_improved": False,
                    "status": "transcribed",
                    "page_id": "456e4567-e89b-12d3-a456-426614174000",
                    "createdAt": "2024-01-15T12:00:00Z",
                    "updatedAt": "2024-01-15T14:30:00Z"
                }
            }
        }
    )
