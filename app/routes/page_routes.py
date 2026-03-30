"""Page route handlers."""

import json
import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.core.dependencies import DbSession, CurrentUserId
from app.schemas.entry import EntryResponse
from app.schemas.page import PageListResponse, PageResponse, PageUpdateRequest, ProcessPageResponse, SinglePageResponse
from app.repositories.page_repository import PageRepository
from app.repositories.entry_repository import EntryRepository
from app.services.page_service import PageService

logger = logging.getLogger("page_routes")

router = APIRouter(prefix="/pages", tags=["Pages"])


def get_page_service(db: DbSession) -> PageService:
    """Dependency to get PageService with repositories."""
    page_repo = PageRepository(db)
    entry_repo = EntryRepository(db)
    return PageService(page_repo, entry_repo)


@router.post(
    "/batch",
    response_model=PageListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload page images (batch)",
    responses={
        400: {"description": "Invalid image, missing fields, or metadata mismatch"},
        401: {"description": "Not authenticated"},
        413: {"description": "File too large"},
    }
)
async def upload_pages_batch(
    user_id: CurrentUserId,
    images: list[UploadFile] = File(..., description="One or more image files (jpg, png, gif, webp)"),
    date: date = Form(..., description="Shared upload date (YYYY-MM-DD)"),
    metadata: str = Form("[]", description='JSON array of per-file metadata, e.g. [{"pageStartDate":"2024-01-01"},{}]'),
    page_service: PageService = Depends(get_page_service),
):
    """
    Upload one or more journal page images in a single request.

    Each image is paired with its metadata entry by index. The metadata
    JSON array must be the same length as the number of uploaded files
    (or empty `[]` to default every start date to null).
    """
    try:
        parsed_meta = json.loads(metadata)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "metadata must be valid JSON"},
        )

    if not isinstance(parsed_meta, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "metadata must be a JSON array"},
        )

    # Pad metadata to match file count when caller sends []
    if len(parsed_meta) == 0:
        parsed_meta = [{}] * len(images)

    page_start_dates: list[date | None] = []
    for item in parsed_meta:
        raw = item.get("pageStartDate") if isinstance(item, dict) else None
        if raw:
            try:
                page_start_dates.append(date.fromisoformat(raw))
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": f"Invalid date in metadata: {raw}"},
                )
        else:
            page_start_dates.append(None)

    try:
        pages = await page_service.upload_pages_batch(
            user_id=user_id,
            images=images,
            uploaded_date=date,
            page_start_dates=page_start_dates,
        )
    except ValueError as e:
        error_msg = str(e)
        if "too large" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={"message": error_msg},
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": error_msg},
        )

    return PageListResponse(
        pages=[
            PageResponse(
                id=p["id"],
                imageUrl=p["image_url"],
                date=p["uploaded_date"],
                page_start_date=p["page_start_date"],
                page_end_date=p["page_end_date"],
                notes=p["notes"],
                status=p["page_status"],
                createdAt=p["created_at"],
            )
            for p in pages
        ],
        total=len(pages),
    )


@router.get(
    "",
    response_model=PageListResponse,
    summary="List all pages",
    responses={
        401: {"description": "Not authenticated"},
    }
)
async def list_pages(
    user_id: CurrentUserId,
    page_service: PageService = Depends(get_page_service),
    start_date: date | None = Query(None, alias="startDate", description="Filter start date (YYYY-MM-DD)"),
    end_date: date | None = Query(None, alias="endDate", description="Filter end date (YYYY-MM-DD)"),
    sortBy: str = Query("date_written", description="Sort field: 'date_written' or 'date_uploaded'"),
    filterField: str = Query("date_written", description="Filter field: 'date_written' or 'date_uploaded'"),
):
    """
    List all pages for the current user.

    Optionally filter by date range. When filterField is 'date_written', filters by
    written-date overlap (both bounds required). When filterField is 'date_uploaded',
    filters by uploaded_date. Default sort is by written date (page_start_date) with
    pages lacking a written date sorted last.
    """
    sort_by_col = "uploaded_date" if sortBy == "date_uploaded" else "page_start_date"
    filter_field_col = "uploaded_date" if filterField == "date_uploaded" else "page_start_date"

    pages = await page_service.get_all_pages(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by_col,
        filter_field=filter_field_col,
    )
    return PageListResponse(
        pages=[
            PageResponse(
                id=p["id"],
                imageUrl=p["image_url"],
                date=p["uploaded_date"],
                page_start_date=p["page_start_date"],
                page_end_date=p["page_end_date"],
                notes=p["notes"],
                status=p["page_status"],
                createdAt=p["created_at"],
            )
            for p in pages
        ],
        total=len(pages),
    )


@router.get(
    "/{page_id}",
    response_model=SinglePageResponse,
    summary="Get a page",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Page belongs to another user"},
        404: {"description": "Page not found"},
    }
)
async def get_page(
    page_id: UUID,
    user_id: CurrentUserId,
    page_service: PageService = Depends(get_page_service)
):
    """
    Get a page by ID.
    
    Returns page information including the full image URL.
    """
    try:
        page = await page_service.get_page(page_id, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": str(e)}
        )
    
    return SinglePageResponse(
        page=PageResponse(
            id=page["id"],
            imageUrl=page["image_url"],
            date=page["uploaded_date"],
            page_start_date=page["page_start_date"],
            page_end_date=page["page_end_date"],
            notes=page["notes"],
            status=page["page_status"],
            createdAt=page["created_at"]
        )
    )


@router.post(
    "/{page_id}/process",
    response_model=ProcessPageResponse,
    summary="Process a page",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Page not found"},
        422: {"description": "OCR or transcription processing returned no results"},
    }
)
async def process_page(
    page_id: UUID,
    user_id: CurrentUserId,
    page_service: PageService = Depends(get_page_service)
):
    """
    Run OCR and transcription processing on an existing page.

    Sends the page image to the configured OCR model, splits the resulting
    text into dated entries via the transcription processing service, and
    saves them to the database. Any previously created entries for this page
    are replaced. The page status is updated to 'transcribed'.

    Returns the updated page and the list of created entries.
    """
    try:
        result = await page_service.process_page(page_id, user_id)
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": error_msg}
            )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": error_msg}
        )

    page = result["page"]
    return ProcessPageResponse(
        page=PageResponse(
            id=page["id"],
            imageUrl=page["image_url"],
            date=page["uploaded_date"],
            page_start_date=page["page_start_date"],
            page_end_date=page["page_end_date"],
            notes=page["notes"],
            status=page["page_status"],
            createdAt=page["created_at"],
        ),
        entries=[
            EntryResponse(
                id=e["id"],
                date=e["entry_date"],
                raw_ocr_transcription=e["raw_ocr_transcription"],
                improved_transcription=e["improved_transcription"],
                agent_has_improved=e["agent_has_improved"],
                page_id=e["page_id"],
                createdAt=e["created_at"],
                updatedAt=e["updated_at"],
            )
            for e in result["entries"]
        ],
    )


@router.patch(
    "/{page_id}",
    response_model=SinglePageResponse,
    summary="Update a page",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Page belongs to another user"},
        404: {"description": "Page not found"},
    }
)
async def update_page(
    page_id: UUID,
    body: PageUpdateRequest,
    user_id: CurrentUserId,
    page_service: PageService = Depends(get_page_service)
):
    """
    Update a page's editable fields.

    Both `page_start_date` and `notes` are optional; only provided fields
    are changed.
    """
    try:
        page = await page_service.update_page(
            page_id=page_id,
            user_id=user_id,
            page_start_date=body.page_start_date,
            notes=body.notes,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": str(e)}
        )

    return SinglePageResponse(
        page=PageResponse(
            id=page["id"],
            imageUrl=page["image_url"],
            date=page["uploaded_date"],
            page_start_date=page["page_start_date"],
            page_end_date=page["page_end_date"],
            notes=page["notes"],
            status=page["page_status"],
            createdAt=page["created_at"]
        )
    )


@router.delete(
    "/{page_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a page",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Page belongs to another user"},
        404: {"description": "Page not found"},
    }
)
async def delete_page(
    page_id: UUID,
    user_id: CurrentUserId,
    page_service: PageService = Depends(get_page_service)
):
    """
    Delete a page and all its associated entries.
    
    Also deletes the image file from storage.
    """
    try:
        await page_service.delete_page(page_id, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": str(e)}
        )
    
    return None
