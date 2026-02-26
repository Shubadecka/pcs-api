"""FastAPI dependency injection setup."""

from typing import Annotated, AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_user_id_from_token


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.
    
    Usage:
        @router.get("/items")
        async def get_items(db: Annotated[AsyncSession, Depends(get_db)]):
            ...
    """
    async for session in get_db_session():
        yield session


# Type alias for database dependency
DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_token_from_cookie(request: Request) -> str | None:
    """Extract JWT token from httpOnly cookie."""
    return request.cookies.get("access_token")


async def get_current_user_id(request: Request) -> UUID:
    """
    Dependency that extracts and validates the current user from JWT cookie.
    
    Raises:
        HTTPException: 401 if not authenticated
        
    Returns:
        The authenticated user's UUID
    """
    token = get_token_from_cookie(request)
    
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    user_id = get_user_id_from_token(token)
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    
    return user_id


# Type alias for current user dependency
CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]


async def get_optional_user_id(request: Request) -> UUID | None:
    """
    Dependency that optionally extracts the current user from JWT cookie.
    Returns None if not authenticated instead of raising an exception.
    """
    token = get_token_from_cookie(request)
    
    if token is None:
        return None
    
    return get_user_id_from_token(token)


# Type alias for optional user dependency
OptionalUserId = Annotated[UUID | None, Depends(get_optional_user_id)]
