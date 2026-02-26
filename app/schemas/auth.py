"""Authentication-related Pydantic schemas."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class RegisterRequest(BaseModel):
    """Schema for user registration request."""
    
    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="User's display name"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User's password (min 8 characters)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "password": "securepassword123"
            }
        }
    )


class LoginRequest(BaseModel):
    """Schema for user login request."""
    
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }
    )


class UserResponse(BaseModel):
    """Schema for user data in responses."""
    
    id: UUID = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    username: str = Field(..., description="User's display name")
    created_at: datetime = Field(..., alias="createdAt", description="Account creation timestamp")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "username": "johndoe",
                "createdAt": "2024-01-15T10:30:00Z"
            }
        }
    )


class AuthResponse(BaseModel):
    """Schema for authentication response (login/register)."""
    
    user: UserResponse = Field(..., description="User information")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "user@example.com",
                    "username": "johndoe",
                    "createdAt": "2024-01-15T10:30:00Z"
                }
            }
        }
    )


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    
    message: str = Field(..., description="Error description")
    error: str | None = Field(None, description="Optional detailed error")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Invalid email or password",
                "error": None
            }
        }
    )
