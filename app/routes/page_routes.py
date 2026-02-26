"""Page route handlers."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.core.dependencies import DbSession, CurrentUserId
from app.schemas.page import PageListResponse, PageResponse, SinglePageResponse
from app.repositories.page_repository import PageRepository
from app.services.page_service import PageService


router = APIRouter(prefix="/pages", tags=["Pages"])


def get_page_service(db: DbSession) -> PageService:
    """Dependency to get PageService with repositories."""
    page_repo = PageRepository(db)
    return PageService(page_repo)


@router.post(
    "",
    response_model=SinglePageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new page",
    responses={
        400: {"description": "Invalid image or missing required fields"},
        401: {"description": "Not authenticated"},
        413: {"description": "File too large"},
    }
)
async def upload_page(
    user_id: CurrentUserId,
    image: UploadFile = File(..., description="Image file (jpg, png, gif, webp)"),
    date: date = Form(..., description="Journal page date (YYYY-MM-DD)"),
    notes: str | None = Form(None, description="Optional notes about the page"),
    page_service: PageService = Depends(get_page_service)
):
    """
    Upload a new journal page image.
    
    Creates a page record with status 'pending'.
    Entries are created later when the page is transcribed.
    """
    try:
        page = await page_service.upload_page(
            user_id=user_id,
            image=image,
            uploaded_date=date,
            notes=notes
        )
    except ValueError as e:
        error_msg = str(e)
        if "too large" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={"message": error_msg}
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": error_msg}
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
    start_date: date | None = Query(None, alias="startDate", description="Filter start date (written date, YYYY-MM-DD)"),
    end_date: date | None = Query(None, alias="endDate", description="Filter end date (written date, YYYY-MM-DD)"),
):
    """
    List all pages for the current user.

    Optionally filter by written date range using startDate and endDate.
    Only pages whose written date range overlaps with the filter range are returned.
    Pages without a written date (status 'pending') are excluded when a filter is active.
    """
    pages = await page_service.get_all_pages(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
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
