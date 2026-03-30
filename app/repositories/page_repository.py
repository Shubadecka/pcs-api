"""Page repository implementation using SQLAlchemy."""

from datetime import date
from uuid import UUID
from typing import Any

from sqlalchemy import select, update, delete, exists, nulls_last
from sqlalchemy.ext.asyncio import AsyncSession

from app.interfaces.repositories.page_repository import IPageRepository
from app.core.models import pages

_UNSET = object()  # sentinel: distinguishes "not passed" from None


class PageRepository(IPageRepository):
    """Repository for page data access operations using SQLAlchemy."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the repository with a database session.
        
        Args:
            db: The SQLAlchemy async session
        """
        self.db = db
    
    async def create(
        self,
        user_id: UUID,
        image_path: str,
        uploaded_date: date,
        page_start_date: date | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Create a new page record."""
        stmt = (
            pages.insert()
            .values(
                user_id=user_id,
                image_path=image_path,
                uploaded_date=uploaded_date,
                page_start_date=page_start_date,
                notes=notes,
                page_status="pending"
            )
            .returning(
                pages.c.id,
                pages.c.user_id,
                pages.c.image_path,
                pages.c.uploaded_date,
                pages.c.page_start_date,
                pages.c.page_end_date,
                pages.c.notes,
                pages.c.page_status,
                pages.c.created_at
            )
        )
        result = await self.db.execute(stmt)
        row = result.fetchone()
        return dict(row._mapping)
    
    async def get_by_id(
        self,
        page_id: UUID,
        user_id: UUID
    ) -> dict[str, Any] | None:
        """Get a page by ID for a specific user."""
        stmt = select(
            pages.c.id,
            pages.c.user_id,
            pages.c.image_path,
            pages.c.uploaded_date,
            pages.c.page_start_date,
            pages.c.page_end_date,
            pages.c.notes,
            pages.c.page_status,
            pages.c.created_at
        ).where(
            pages.c.id == page_id,
            pages.c.user_id == user_id
        )
        
        result = await self.db.execute(stmt)
        row = result.fetchone()
        return dict(row._mapping) if row else None
    
    async def update_status(
        self,
        page_id: UUID,
        user_id: UUID,
        page_status: str,
        page_start_date: date | None = _UNSET,
        page_end_date: date | None = _UNSET,
    ) -> dict[str, Any] | None:
        """Update a page's status, and optionally its date range.

        Date columns are only written when explicitly provided; omitting them
        leaves whatever is already stored in the database untouched.
        """
        values: dict = {"page_status": page_status}
        if page_start_date is not _UNSET:
            values["page_start_date"] = page_start_date
        if page_end_date is not _UNSET:
            values["page_end_date"] = page_end_date

        stmt = (
            update(pages)
            .where(
                pages.c.id == page_id,
                pages.c.user_id == user_id
            )
            .values(**values)
            .returning(
                pages.c.id,
                pages.c.user_id,
                pages.c.image_path,
                pages.c.uploaded_date,
                pages.c.page_start_date,
                pages.c.page_end_date,
                pages.c.notes,
                pages.c.page_status,
                pages.c.created_at
            )
        )
        
        result = await self.db.execute(stmt)
        row = result.fetchone()
        return dict(row._mapping) if row else None
    
    async def delete(self, page_id: UUID, user_id: UUID) -> bool:
        """Delete a page."""
        stmt = delete(pages).where(
            pages.c.id == page_id,
            pages.c.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0
    
    async def exists(self, page_id: UUID, user_id: UUID) -> bool:
        """Check if a page exists and is owned by the user."""
        stmt = select(
            exists().where(
                pages.c.id == page_id,
                pages.c.user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or False
    
    async def get_all_by_user(
        self,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        sort_by: str = "page_start_date",
        filter_field: str = "page_start_date",
    ) -> list[dict[str, Any]]:
        """Get all pages for a user, with optional date range filter."""
        stmt = select(
            pages.c.id,
            pages.c.user_id,
            pages.c.image_path,
            pages.c.uploaded_date,
            pages.c.page_start_date,
            pages.c.page_end_date,
            pages.c.notes,
            pages.c.page_status,
            pages.c.created_at
        ).where(pages.c.user_id == user_id)

        if filter_field == "uploaded_date":
            if start_date:
                stmt = stmt.where(pages.c.uploaded_date >= start_date)
            if end_date:
                stmt = stmt.where(pages.c.uploaded_date <= end_date)
        else:
            # Written-date overlap filter (requires both bounds)
            if start_date and end_date:
                stmt = stmt.where(
                    pages.c.page_start_date <= end_date,
                    pages.c.page_end_date >= start_date,
                )

        if sort_by == "uploaded_date":
            stmt = stmt.order_by(pages.c.uploaded_date.desc())
        else:
            stmt = stmt.order_by(nulls_last(pages.c.page_start_date.desc()))

        result = await self.db.execute(stmt)
        return [dict(r._mapping) for r in result.fetchall()]

    async def update_dates(
        self,
        page_id: UUID,
        user_id: UUID,
        page_start_date: date | None = None,
    ) -> dict[str, Any] | None:
        """Update a page's start date without touching status or end date."""
        stmt = (
            update(pages)
            .where(
                pages.c.id == page_id,
                pages.c.user_id == user_id
            )
            .values(page_start_date=page_start_date)
            .returning(
                pages.c.id,
                pages.c.user_id,
                pages.c.image_path,
                pages.c.uploaded_date,
                pages.c.page_start_date,
                pages.c.page_end_date,
                pages.c.notes,
                pages.c.page_status,
                pages.c.created_at
            )
        )
        result = await self.db.execute(stmt)
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def get_image_path(self, page_id: UUID, user_id: UUID) -> str | None:
        """Get the image path for a page."""
        stmt = select(pages.c.image_path).where(
            pages.c.id == page_id,
            pages.c.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalar()
