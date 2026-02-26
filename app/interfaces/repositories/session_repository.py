"""Interface for session repository."""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID
from typing import Any


class ISessionRepository(ABC):
    """Abstract base class for session data access operations."""
    
    @abstractmethod
    async def create(
        self,
        user_id: UUID,
        session_token: str,
        expires_at: datetime
    ) -> dict[str, Any]:
        """
        Create a new session.
        
        Args:
            user_id: The user's UUID
            session_token: The session token
            expires_at: When the session expires
            
        Returns:
            The created session record
        """
        ...
    
    @abstractmethod
    async def get_by_token(self, session_token: str) -> dict[str, Any] | None:
        """
        Get a session by token.
        
        Args:
            session_token: The session token to look up
            
        Returns:
            The session record if found and not expired, None otherwise
        """
        ...
    
    @abstractmethod
    async def delete(self, session_token: str) -> bool:
        """
        Delete a session by token.
        
        Args:
            session_token: The session token to delete
            
        Returns:
            True if deleted, False if not found
        """
        ...
    
    @abstractmethod
    async def delete_by_user_id(self, user_id: UUID) -> int:
        """
        Delete all sessions for a user.
        
        Args:
            user_id: The user's UUID
            
        Returns:
            Number of sessions deleted
        """
        ...
    
    @abstractmethod
    async def delete_expired(self) -> int:
        """
        Delete all expired sessions.
        
        Returns:
            Number of sessions deleted
        """
        ...
