"""Interfaces module containing abstract base classes for repositories and services."""

from app.interfaces.repositories import (
    IUserRepository,
    ISessionRepository,
    IEntryRepository,
    IPageRepository,
)
from app.interfaces.services import (
    IAuthService,
    IEntryService,
    IPageService,
)

__all__ = [
    # Repository interfaces
    "IUserRepository",
    "ISessionRepository",
    "IEntryRepository",
    "IPageRepository",
    # Service interfaces
    "IAuthService",
    "IEntryService",
    "IPageService",
]
