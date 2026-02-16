"""Session repository implementation using SQLAlchemy."""

from datetime import datetime
from uuid import UUID
from typing import Any

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.interfaces.repositories.session_repository import ISessionRepository
from app.core.models import sessions


class SessionRepository(ISessionRepository):
    """Repository for session data access operations using SQLAlchemy."""
    
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
        session_token: str,
        expires_at: datetime
    ) -> dict[str, Any]:
        """Create a new session."""
        stmt = (
            sessions.insert()
            .values(
                user_id=user_id,
                session_token=session_token,
                expires_at=expires_at
            )
            .returning(
                sessions.c.id,
                sessions.c.user_id,
                sessions.c.session_token,
                sessions.c.expires_at,
                sessions.c.created_at
            )
        )
        result = await self.db.execute(stmt)
        row = result.fetchone()
        return dict(row._mapping)
    
    async def get_by_token(self, session_token: str) -> dict[str, Any] | None:
        """Get a session by token (only if not expired)."""
        stmt = select(
            sessions.c.id,
            sessions.c.user_id,
            sessions.c.session_token,
            sessions.c.expires_at,
            sessions.c.created_at
        ).where(
            sessions.c.session_token == session_token,
            sessions.c.expires_at > func.now()
        )
        
        result = await self.db.execute(stmt)
        row = result.fetchone()
        return dict(row._mapping) if row else None
    
    async def delete(self, session_token: str) -> bool:
        """Delete a session by token."""
        stmt = delete(sessions).where(sessions.c.session_token == session_token)
        result = await self.db.execute(stmt)
        return result.rowcount > 0
    
    async def delete_by_user_id(self, user_id: UUID) -> int:
        """Delete all sessions for a user."""
        stmt = delete(sessions).where(sessions.c.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.rowcount
    
    async def delete_expired(self) -> int:
        """Delete all expired sessions."""
        stmt = delete(sessions).where(sessions.c.expires_at <= func.now())
        result = await self.db.execute(stmt)
        return result.rowcount
