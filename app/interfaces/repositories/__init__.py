"""Repository interfaces for data access layer."""

from app.interfaces.repositories.user_repository import IUserRepository
from app.interfaces.repositories.session_repository import ISessionRepository
from app.interfaces.repositories.entry_repository import IEntryRepository
from app.interfaces.repositories.page_repository import IPageRepository

__all__ = [
    "IUserRepository",
    "ISessionRepository",
    "IEntryRepository",
    "IPageRepository",
]
