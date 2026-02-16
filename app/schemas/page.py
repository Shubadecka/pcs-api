"""Page-related Pydantic schemas."""

from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class PageResponse(BaseModel):
    """Schema for page data in responses."""
    
    id: UUID = Field(..., description="Page's unique identifier")
    image_url: str = Field(..., alias="imageUrl", description="Full URL to the image file")
    uploaded_date: date = Field(..., alias="date", description="Date the page was uploaded")
    page_start_date: date | None = Field(None, description="First journal date on this page")
    page_end_date: date | None = Field(None, description="Last journal date on this page")
    notes: str | None = Field(None, description="Optional notes about the page")
    page_status: str = Field(..., alias="status", description="Page status (pending or transcribed)")
    created_at: datetime = Field(..., alias="createdAt", description="Upload timestamp")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "imageUrl": "http://localhost:1442/uploads/page-123.jpg",
                "date": "2024-01-15",
                "page_start_date": "2024-01-15",
                "page_end_date": "2024-01-15",
                "notes": "Morning journal entry",
                "status": "pending",
                "createdAt": "2024-01-15T10:00:00Z"
            }
        }
    )


class SinglePageResponse(BaseModel):
    """Schema for single page response wrapper."""
    
    page: PageResponse = Field(..., description="The page data")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "imageUrl": "http://localhost:1442/uploads/page-123.jpg",
                    "date": "2024-01-15",
                    "page_start_date": None,
                    "page_end_date": None,
                    "notes": "Morning journal entry",
                    "status": "pending",
                    "createdAt": "2024-01-15T10:00:00Z"
                }
            }
        }
    )


class PageListResponse(BaseModel):
    """Schema for paginated page list response."""
    
    pages: list[PageResponse] = Field(..., description="List of pages")
    total: int = Field(..., description="Total number of pages")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pages": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "imageUrl": "http://localhost:1442/uploads/page-123.jpg",
                        "date": "2024-01-15",
                        "page_start_date": None,
                        "page_end_date": None,
                        "notes": "Morning journal entry",
                        "status": "pending",
                        "createdAt": "2024-01-15T10:00:00Z"
                    }
                ],
                "total": 1
            }
        }
    )
