"""Pydantic schemas for request/response validation."""

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    AuthResponse,
)
from app.schemas.entry import (
    EntryResponse,
    EntryUpdate,
    EntryListResponse,
)
from app.schemas.page import (
    PageResponse,
    PageListResponse,
)

__all__ = [
    # Auth schemas
    "RegisterRequest",
    "LoginRequest",
    "UserResponse",
    "AuthResponse",
    # Entry schemas
    "EntryResponse",
    "EntryUpdate",
    "EntryListResponse",
    # Page schemas
    "PageResponse",
    "PageListResponse",
]
