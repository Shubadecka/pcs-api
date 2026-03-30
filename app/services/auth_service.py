"""Authentication service implementation."""

import re
from uuid import UUID
from typing import Any

from app.interfaces.services.auth_service import IAuthService
from app.interfaces.repositories.user_repository import IUserRepository
from app.core.config import settings
from app.core.security import (
    generate_salt,
    hash_password,
    verify_password,
    create_jwt_token,
)


class AuthService(IAuthService):
    """Service for authentication business logic."""
    
    # Email validation regex
    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    
    # Minimum password length
    MIN_PASSWORD_LENGTH = 8
    
    def __init__(self, user_repository: IUserRepository):
        """
        Initialize the service with required repositories.
        
        Args:
            user_repository: Repository for user data access
        """
        self.user_repository = user_repository
    
    async def register(
        self,
        email: str,
        username: str,
        password: str
    ) -> tuple[dict[str, Any], str]:
        """Register a new user."""
        # Validate email format
        if not await self.validate_email(email):
            raise ValueError("Invalid email format")

        # Enforce domain allowlist if enabled
        if settings.restrict_email_domains:
            domain = email.split("@", 1)[-1].lower()
            if domain not in settings.allowed_email_domains_list:
                raise ValueError("Registration is not open for your email domain")
        
        # Validate password
        if not await self.validate_password(password):
            raise ValueError(f"Password must be at least {self.MIN_PASSWORD_LENGTH} characters")
        
        # Validate username
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters")
        
        # Check if email already exists
        if await self.user_repository.email_exists(email):
            raise ValueError("Email already registered")
        
        # Check if username already exists
        if await self.user_repository.username_exists(username):
            raise ValueError("Username already taken")
        
        # Generate salt and hash password
        salt = generate_salt()
        password_hash = hash_password(password, salt)
        
        # Create user
        user = await self.user_repository.create(
            email=email,
            username=username,
            password_hash=password_hash,
            salt=salt
        )
        
        # Generate JWT token
        token = create_jwt_token(user["id"])
        
        # Return user (without sensitive fields) and token
        return {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "created_at": user["created_at"],
        }, token
    
    async def login(
        self,
        username: str,
        password: str
    ) -> tuple[dict[str, Any], str]:
        """Authenticate a user."""
        user = await self.user_repository.get_by_username(username)
        
        if user is None:
            raise ValueError("Invalid username or password")
        
        # Verify password
        if not verify_password(password, user["salt"], user["password_hash"]):
            raise ValueError("Invalid username or password")
        
        # Generate JWT token
        token = create_jwt_token(user["id"])
        
        # Return user (without sensitive fields) and token
        return {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "created_at": user["created_at"],
        }, token
    
    async def logout(self, token: str) -> None:
        """
        Log out a user.
        
        Note: With JWT stored in httpOnly cookies, logout is handled by
        clearing the cookie on the client side. This method is a no-op
        but kept for interface compliance and potential future session tracking.
        """
        # JWT tokens are stateless - logout is handled by clearing the cookie
        # If we implement a token blacklist in the future, it would go here
        pass
    
    async def get_current_user(self, user_id: UUID) -> dict[str, Any] | None:
        """Get the current user's information."""
        user = await self.user_repository.get_by_id(user_id)
        
        if user is None:
            return None
        
        return {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "created_at": user["created_at"],
        }
    
    async def validate_email(self, email: str) -> bool:
        """Validate an email format."""
        return bool(self.EMAIL_REGEX.match(email))
    
    async def validate_password(self, password: str) -> bool:
        """Validate a password meets requirements."""
        return len(password) >= self.MIN_PASSWORD_LENGTH
