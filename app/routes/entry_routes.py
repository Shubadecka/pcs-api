"""Entry route handlers."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import DbSession, CurrentUserId
from app.schemas.entry import (
    EntryResponse,
    EntryUpdate,
    EntryListResponse,
    SingleEntryResponse,
)
from app.repositories.entry_repository import EntryRepository
from app.services.entry_service import EntryService


router = APIRouter(prefix="/entries", tags=["Entries"])


def get_entry_service(db: DbSession) -> EntryService:
    """Dependency to get EntryService with repositories."""
    entry_repo = EntryRepository(db)
    return EntryService(entry_repo)


@router.get(
    "",
    response_model=EntryListResponse,
    summary="Get all entries",
    responses={
        401: {"description": "Not authenticated"},
    }
)
async def get_entries(
    user_id: CurrentUserId,
    entry_service: EntryService = Depends(get_entry_service),
    startDate: date | None = Query(None, description="Filter by start date (inclusive)"),
    endDate: date | None = Query(None, description="Filter by end date (inclusive)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page")
):
    """
    Get all entries for the current user.
    
    Supports optional date filtering and pagination.
    """
    entries, total = await entry_service.get_entries(
        user_id=user_id,
        start_date=startDate,
        end_date=endDate,
        page=page,
        limit=limit
    )
    
    return EntryListResponse(
        entries=[
            EntryResponse(
                id=entry["id"],
                date=entry["entry_date"],
                transcription=entry["transcription"],
                page_id=entry["page_id"],
                createdAt=entry["created_at"],
                updatedAt=entry["updated_at"],
                status=entry["status"]
            )
            for entry in entries
        ],
        total=total
    )


@router.get(
    "/{entry_id}",
    response_model=SingleEntryResponse,
    summary="Get a single entry",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Entry belongs to another user"},
        404: {"description": "Entry not found"},
    }
)
async def get_entry(
    entry_id: UUID,
    user_id: CurrentUserId,
    entry_service: EntryService = Depends(get_entry_service)
):
    """
    Get a single entry by ID.
    """
    try:
        entry = await entry_service.get_entry(entry_id, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": str(e)}
        )
    
    return SingleEntryResponse(
        entry=EntryResponse(
            id=entry["id"],
            date=entry["entry_date"],
            transcription=entry["transcription"],
            page_id=entry["page_id"],
            createdAt=entry["created_at"],
            updatedAt=entry["updated_at"],
            status=entry["status"]
        )
    )


@router.put(
    "/{entry_id}",
    response_model=SingleEntryResponse,
    summary="Update an entry",
    responses={
        400: {"description": "Invalid date format"},
        401: {"description": "Not authenticated"},
        403: {"description": "Entry belongs to another user"},
        404: {"description": "Entry not found"},
    }
)
async def update_entry(
    entry_id: UUID,
    request: EntryUpdate,
    user_id: CurrentUserId,
    entry_service: EntryService = Depends(get_entry_service)
):
    """
    Update an entry's date or transcription.
    
    All fields are optional - only include fields you want to update.
    """
    try:
        entry = await entry_service.update_entry(
            entry_id=entry_id,
            user_id=user_id,
            entry_date=request.entry_date,
            transcription=request.transcription
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": str(e)}
        )
    
    return SingleEntryResponse(
        entry=EntryResponse(
            id=entry["id"],
            date=entry["entry_date"],
            transcription=entry["transcription"],
            page_id=entry["page_id"],
            createdAt=entry["created_at"],
            updatedAt=entry["updated_at"],
            status=entry["status"]
        )
    )


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an entry",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Entry belongs to another user"},
        404: {"description": "Entry not found"},
    }
)
async def delete_entry(
    entry_id: UUID,
    user_id: CurrentUserId,
    entry_service: EntryService = Depends(get_entry_service)
):
    """
    Delete an entry.
    
    Does NOT delete the associated page image.
    """
    try:
        await entry_service.delete_entry(entry_id, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": str(e)}
        )
    
    return None
