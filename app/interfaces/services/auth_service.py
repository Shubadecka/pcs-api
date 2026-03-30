"""Interface for authentication service."""

from abc import ABC, abstractmethod
from uuid import UUID
from typing import Any


class IAuthService(ABC):
    """Abstract base class for authentication operations."""
    
    @abstractmethod
    async def register(
        self,
        email: str,
        username: str,
        password: str
    ) -> tuple[dict[str, Any], str]:
        """
        Register a new user.
        
        Args:
            email: User's email address
            username: User's display name
            password: User's plain text password
            
        Returns:
            Tuple of (user record, JWT token)
            
        Raises:
            ValueError: If email already exists or validation fails
        """
        ...
    
    @abstractmethod
    async def login(
        self,
        username: str,
        password: str
    ) -> tuple[dict[str, Any], str]:
        """
        Authenticate a user.
        
        Args:
            username: User's username
            password: User's plain text password
            
        Returns:
            Tuple of (user record, JWT token)
            
        Raises:
            ValueError: If credentials are invalid
        """
        ...
    
    @abstractmethod
    async def logout(self, token: str) -> None:
        """
        Log out a user by invalidating their session.
        
        Args:
            token: The session token to invalidate
        """
        ...
    
    @abstractmethod
    async def get_current_user(self, user_id: UUID) -> dict[str, Any] | None:
        """
        Get the current user's information.
        
        Args:
            user_id: The user's UUID
            
        Returns:
            The user record if found, None otherwise
        """
        ...
    
    @abstractmethod
    async def validate_email(self, email: str) -> bool:
        """
        Validate an email format.
        
        Args:
            email: The email to validate
            
        Returns:
            True if valid, False otherwise
        """
        ...
    
    @abstractmethod
    async def validate_password(self, password: str) -> bool:
        """
        Validate a password meets requirements.
        
        Args:
            password: The password to validate
            
        Returns:
            True if valid, False otherwise
        """
        ...
