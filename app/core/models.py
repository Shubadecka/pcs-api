"""SQLAlchemy table definitions and Pydantic models for database records."""

from datetime import datetime, date
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import (
    MetaData,
    Table,
    Column,
    String,
    Text,
    Date,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


# =============================================================================
# SQLAlchemy Table Definitions
# =============================================================================

# Metadata instance for all tables
metadata = MetaData()


# Users table
users = Table(
    "users",
    metadata,
    Column("id", PG_UUID(as_uuid=True), primary_key=True, default=uuid4),
    Column("email", String(255), nullable=False, unique=True),
    Column("username", String(255), nullable=False, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("salt", String(255), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    
    # Indexes
    Index("idx_users_email", "email"),
    Index("idx_users_username", "username"),
)


# Sessions table
sessions = Table(
    "sessions",
    metadata,
    Column("id", PG_UUID(as_uuid=True), primary_key=True, default=uuid4),
    Column("user_id", PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("session_token", String(255), nullable=False, unique=True),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    
    # Indexes
    Index("idx_sessions_token", "session_token"),
    Index("idx_sessions_expires_at", "expires_at"),
    Index("idx_sessions_user_id", "user_id"),
)


# Pages table
pages = Table(
    "pages",
    metadata,
    Column("id", PG_UUID(as_uuid=True), primary_key=True, default=uuid4),
    Column("user_id", PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("image_path", String(512), nullable=False),
    Column("uploaded_date", Date, nullable=False),
    Column("page_start_date", Date, nullable=True),
    Column("page_end_date", Date, nullable=True),
    Column("notes", Text, nullable=True),
    Column("page_status", String(20), nullable=False, server_default="pending"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    
    # Constraints
    CheckConstraint("page_status IN ('pending', 'transcribed')", name="check_page_status"),
    
    # Indexes
    Index("idx_pages_user_id", "user_id"),
    Index("idx_pages_user_uploaded_date", "user_id", "uploaded_date"),
    Index("idx_pages_user_page_status", "user_id", "page_status"),
    Index("idx_pages_user_date_range", "user_id", "page_start_date", "page_end_date"),
)


# Entries table
entries = Table(
    "entries",
    metadata,
    Column("id", PG_UUID(as_uuid=True), primary_key=True, default=uuid4),
    Column("user_id", PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("page_id", PG_UUID(as_uuid=True), ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
    Column("entry_date", Date, nullable=False),
    Column("transcription", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    
    # Indexes
    Index("idx_entries_user_id", "user_id"),
    Index("idx_entries_user_entry_date", "user_id", "entry_date"),
    Index("idx_entries_page_id", "page_id"),
)


# =============================================================================
# Pydantic Models for Database Records
# =============================================================================

class UserModel(BaseModel):
    """Pydantic model for user database records."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique user identifier")
    email: str = Field(..., max_length=255, description="User's email address")
    username: str = Field(..., max_length=255, description="User's display name")
    password_hash: str = Field(..., max_length=255, description="Hashed password")
    salt: str = Field(..., max_length=255, description="Salt for password hashing")
    created_at: datetime = Field(default_factory=datetime.now, description="Account creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class UserPublicModel(BaseModel):
    """Pydantic model for user data without sensitive fields."""
    
    id: UUID = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User's email address")
    username: str = Field(..., description="User's display name")
    created_at: datetime = Field(..., description="Account creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class SessionModel(BaseModel):
    """Pydantic model for session database records."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique session identifier")
    user_id: UUID = Field(..., description="Associated user's UUID")
    session_token: str = Field(..., max_length=255, description="Session token")
    expires_at: datetime = Field(..., description="Session expiration timestamp")
    created_at: datetime = Field(default_factory=datetime.now, description="Session creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class PageModel(BaseModel):
    """Pydantic model for page database records."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique page identifier")
    user_id: UUID = Field(..., description="Owner's UUID")
    image_path: str = Field(..., max_length=512, description="Path to stored image file")
    uploaded_date: date = Field(..., description="Date the page was uploaded")
    page_start_date: date | None = Field(None, description="First journal date on this page")
    page_end_date: date | None = Field(None, description="Last journal date on this page")
    notes: str | None = Field(None, description="Optional notes about the page")
    page_status: str = Field(default="pending", description="Page status (pending or transcribed)")
    created_at: datetime = Field(default_factory=datetime.now, description="Upload timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class EntryModel(BaseModel):
    """Pydantic model for entry database records."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique entry identifier")
    user_id: UUID = Field(..., description="Owner's UUID")
    page_id: UUID = Field(..., description="Associated page's UUID")
    entry_date: date = Field(..., description="Journal entry date")
    transcription: str = Field(..., description="Transcribed text")
    created_at: datetime = Field(default_factory=datetime.now, description="Entry creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last modification timestamp")
    
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Model Creation Helpers
# =============================================================================

class UserCreate(BaseModel):
    """Pydantic model for creating a new user."""
    
    email: str = Field(..., max_length=255)
    username: str = Field(..., max_length=255)
    password_hash: str = Field(..., max_length=255)
    salt: str = Field(..., max_length=255)


class SessionCreate(BaseModel):
    """Pydantic model for creating a new session."""
    
    user_id: UUID
    session_token: str = Field(..., max_length=255)
    expires_at: datetime


class PageCreate(BaseModel):
    """Pydantic model for creating a new page."""
    
    user_id: UUID
    image_path: str = Field(..., max_length=512)
    uploaded_date: date
    notes: str | None = None


class PageUpdate(BaseModel):
    """Pydantic model for updating a page."""
    
    page_status: str | None = None
    page_start_date: date | None = None
    page_end_date: date | None = None


class EntryCreate(BaseModel):
    """Pydantic model for creating a new entry."""
    
    user_id: UUID
    page_id: UUID
    entry_date: date
    transcription: str


class EntryUpdate(BaseModel):
    """Pydantic model for updating an entry."""
    
    entry_date: date | None = None
    transcription: str | None = None
