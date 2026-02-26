"""Interface for user repository."""

from abc import ABC, abstractmethod
from uuid import UUID
from typing import Any


class IUserRepository(ABC):
    """Abstract base class for user data access operations."""
    
    @abstractmethod
    async def create(
        self,
        email: str,
        username: str,
        password_hash: str,
        salt: str
    ) -> dict[str, Any]:
        """
        Create a new user.
        
        Args:
            email: User's email address
            username: User's display name
            password_hash: Hashed password
            salt: Salt used for password hashing
            
        Returns:
            The created user record
        """
        ...
    
    @abstractmethod
    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        """
        Get a user by email address.
        
        Args:
            email: The email to look up
            
        Returns:
            The user record if found, None otherwise
        """
        ...
    
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> dict[str, Any] | None:
        """
        Get a user by ID.
        
        Args:
            user_id: The user's UUID
            
        Returns:
            The user record if found, None otherwise
        """
        ...
    
    @abstractmethod
    async def get_by_username(self, username: str) -> dict[str, Any] | None:
        """
        Get a user by username.
        
        Args:
            username: The username to look up
            
        Returns:
            The user record if found, None otherwise
        """
        ...
    
    @abstractmethod
    async def email_exists(self, email: str) -> bool:
        """
        Check if an email is already registered.
        
        Args:
            email: The email to check
            
        Returns:
            True if the email exists, False otherwise
        """
        ...
    
    @abstractmethod
    async def username_exists(self, username: str) -> bool:
        """
        Check if a username is already taken.
        
        Args:
            username: The username to check
            
        Returns:
            True if the username exists, False otherwise
        """
        ...
