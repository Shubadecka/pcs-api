"""Service interfaces for business logic layer."""

from app.interfaces.services.auth_service import IAuthService
from app.interfaces.services.entry_service import IEntryService
from app.interfaces.services.page_service import IPageService

__all__ = [
    "IAuthService",
    "IEntryService",
    "IPageService",
]
