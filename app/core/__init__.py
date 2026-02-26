"""Core module containing configuration, database, security, and dependency injection."""

from app.core.config import settings
from app.core.database import get_db_session, init_db, close_db
from app.core.security import hash_password, verify_password, create_jwt_token, decode_jwt_token
from app.core.models import (
    # SQLAlchemy tables
    metadata,
    users,
    sessions,
    pages,
    entries,
    # Pydantic models
    UserModel,
    UserPublicModel,
    SessionModel,
    PageModel,
    EntryModel,
    # Creation/Update models
    UserCreate,
    SessionCreate,
    PageCreate,
    PageUpdate,
    EntryCreate,
    EntryUpdate,
)

__all__ = [
    # Config
    "settings",
    # Database
    "get_db_session",
    "init_db",
    "close_db",
    # Security
    "hash_password",
    "verify_password",
    "create_jwt_token",
    "decode_jwt_token",
    # SQLAlchemy tables
    "metadata",
    "users",
    "sessions",
    "pages",
    "entries",
    # Pydantic models
    "UserModel",
    "UserPublicModel",
    "SessionModel",
    "PageModel",
    "EntryModel",
    # Creation/Update models
    "UserCreate",
    "SessionCreate",
    "PageCreate",
    "PageUpdate",
    "EntryCreate",
    "EntryUpdate",
]
