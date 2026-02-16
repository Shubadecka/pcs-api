"""User repository implementation using SQLAlchemy."""

from uuid import UUID
from typing import Any

from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession

from app.interfaces.repositories.user_repository import IUserRepository
from app.core.models import users


class UserRepository(IUserRepository):
    """Repository for user data access operations using SQLAlchemy."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the repository with a database session.
        
        Args:
            db: The SQLAlchemy async session
        """
        self.db = db
    
    async def create(
        self,
        email: str,
        username: str,
        password_hash: str,
        salt: str
    ) -> dict[str, Any]:
        """Create a new user."""
        stmt = (
            users.insert()
            .values(
                email=email,
                username=username,
                password_hash=password_hash,
                salt=salt
            )
            .returning(
                users.c.id,
                users.c.email,
                users.c.username,
                users.c.created_at
            )
        )
        result = await self.db.execute(stmt)
        row = result.fetchone()
        return dict(row._mapping)
    
    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        """Get a user by email address."""
        stmt = select(
            users.c.id,
            users.c.email,
            users.c.username,
            users.c.password_hash,
            users.c.salt,
            users.c.created_at
        ).where(users.c.email == email)
        
        result = await self.db.execute(stmt)
        row = result.fetchone()
        return dict(row._mapping) if row else None
    
    async def get_by_id(self, user_id: UUID) -> dict[str, Any] | None:
        """Get a user by ID."""
        stmt = select(
            users.c.id,
            users.c.email,
            users.c.username,
            users.c.created_at
        ).where(users.c.id == user_id)
        
        result = await self.db.execute(stmt)
        row = result.fetchone()
        return dict(row._mapping) if row else None
    
    async def get_by_username(self, username: str) -> dict[str, Any] | None:
        """Get a user by username."""
        stmt = select(
            users.c.id,
            users.c.email,
            users.c.username,
            users.c.password_hash,
            users.c.salt,
            users.c.created_at
        ).where(users.c.username == username)
        
        result = await self.db.execute(stmt)
        row = result.fetchone()
        return dict(row._mapping) if row else None
    
    async def email_exists(self, email: str) -> bool:
        """Check if an email is already registered."""
        stmt = select(exists().where(users.c.email == email))
        result = await self.db.execute(stmt)
        return result.scalar() or False
    
    async def username_exists(self, username: str) -> bool:
        """Check if a username is already taken."""
        stmt = select(exists().where(users.c.username == username))
        result = await self.db.execute(stmt)
        return result.scalar() or False
