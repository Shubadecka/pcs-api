"""Entry repository implementation using SQLAlchemy."""

from datetime import date
from uuid import UUID
from typing import Any

from sqlalchemy import select, update, delete, exists, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.interfaces.repositories.entry_repository import IEntryRepository
from app.core.models import entries


class EntryRepository(IEntryRepository):
    """Repository for entry data access operations using SQLAlchemy."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the repository with a database session.
        
        Args:
            db: The SQLAlchemy async session
        """
        self.db = db
    
    async def get_all(
        self,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        limit: int = 50
    ) -> tuple[list[dict[str, Any]], int]:
        """Get all entries for a user with optional filtering."""
        # Build filter conditions
        conditions = [entries.c.user_id == user_id]
        
        if start_date is not None:
            conditions.append(entries.c.entry_date >= start_date)
        
        if end_date is not None:
            conditions.append(entries.c.entry_date <= end_date)
        
        # Combine conditions with AND
        where_clause = and_(*conditions)
        
        # Get total count
        count_stmt = select(func.count()).select_from(entries).where(where_clause)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get paginated entries
        stmt = (
            select(
                entries.c.id,
                entries.c.user_id,
                entries.c.page_id,
                entries.c.entry_date,
                entries.c.transcription,
                entries.c.created_at,
                entries.c.updated_at
            )
            .where(where_clause)
            .order_by(entries.c.entry_date.desc(), entries.c.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        result = await self.db.execute(stmt)
        rows = result.fetchall()
        
        return [dict(row._mapping) for row in rows], total
    
    async def get_by_id(
        self,
        entry_id: UUID,
        user_id: UUID
    ) -> dict[str, Any] | None:
        """Get an entry by ID for a specific user."""
        stmt = select(
            entries.c.id,
            entries.c.user_id,
            entries.c.page_id,
            entries.c.entry_date,
            entries.c.transcription,
            entries.c.created_at,
            entries.c.updated_at
        ).where(
            entries.c.id == entry_id,
            entries.c.user_id == user_id
        )
        
        result = await self.db.execute(stmt)
        row = result.fetchone()
        return dict(row._mapping) if row else None
    
    async def create(
        self,
        user_id: UUID,
        page_id: UUID,
        entry_date: date,
        transcription: str
    ) -> dict[str, Any]:
        """Create a new entry."""
        stmt = (
            entries.insert()
            .values(
                user_id=user_id,
                page_id=page_id,
                entry_date=entry_date,
                transcription=transcription
            )
            .returning(
                entries.c.id,
                entries.c.user_id,
                entries.c.page_id,
                entries.c.entry_date,
                entries.c.transcription,
                entries.c.created_at,
                entries.c.updated_at
            )
        )
        result = await self.db.execute(stmt)
        row = result.fetchone()
        return dict(row._mapping)
    
    async def update(
        self,
        entry_id: UUID,
        user_id: UUID,
        entry_date: date | None = None,
        transcription: str | None = None
    ) -> dict[str, Any] | None:
        """Update an entry."""
        # Build update values dictionary
        values: dict[str, Any] = {"updated_at": func.now()}
        
        if entry_date is not None:
            values["entry_date"] = entry_date
        
        if transcription is not None:
            values["transcription"] = transcription
        
        stmt = (
            update(entries)
            .where(
                entries.c.id == entry_id,
                entries.c.user_id == user_id
            )
            .values(**values)
            .returning(
                entries.c.id,
                entries.c.user_id,
                entries.c.page_id,
                entries.c.entry_date,
                entries.c.transcription,
                entries.c.created_at,
                entries.c.updated_at
            )
        )
        
        result = await self.db.execute(stmt)
        row = result.fetchone()
        return dict(row._mapping) if row else None
    
    async def delete(self, entry_id: UUID, user_id: UUID) -> bool:
        """Delete an entry."""
        stmt = delete(entries).where(
            entries.c.id == entry_id,
            entries.c.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0
    
    async def exists(self, entry_id: UUID, user_id: UUID) -> bool:
        """Check if an entry exists and is owned by the user."""
        stmt = select(
            exists().where(
                entries.c.id == entry_id,
                entries.c.user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or False
