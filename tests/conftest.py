"""
Shared test configuration and fixtures.

Environment variables are set here before any app module is imported
so that pydantic-settings picks them up when Settings() is first instantiated.
"""

import os
import uuid
from datetime import date, datetime, timezone

# Must be set before any app imports so pydantic-settings reads them correctly
os.environ.update({
    "DATABASE_HOST": "localhost",
    "DATABASE_PORT": "5432",
    "DATABASE_NAME": "test_db",
    "DATABASE_USER": "postgres",
    "DATABASE_PASSWORD": "test_password",
    "JWT_SECRET_KEY": "test-secret-key-for-testing-only-minimum-length",
    "JWT_ALGORITHM": "HS256",
    "JWT_EXPIRY_HOURS": "24",
})

import pytest


# ---------------------------------------------------------------------------
# Common UUIDs
# ---------------------------------------------------------------------------

@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture
def page_id() -> uuid.UUID:
    return uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture
def entry_id() -> uuid.UUID:
    return uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


# ---------------------------------------------------------------------------
# Common data factories
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_user(user_id):
    return {
        "id": user_id,
        "email": "test@example.com",
        "username": "testuser",
        "password_hash": "$2b$12$fakehash",
        "salt": "fakesalt",
        "created_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_page(page_id, user_id):
    return {
        "id": page_id,
        "user_id": user_id,
        "image_path": f"{user_id}/test-image.jpg",
        "uploaded_date": date(2024, 1, 15),
        "page_start_date": None,
        "page_end_date": None,
        "notes": None,
        "page_status": "pending",
        "created_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_entry(entry_id, user_id, page_id):
    now = datetime.now(timezone.utc)
    return {
        "id": entry_id,
        "user_id": user_id,
        "page_id": page_id,
        "entry_date": date(2024, 1, 15),
        "raw_ocr_transcription": "Today was a good day.",
        "improved_transcription": None,
        "agent_has_improved": False,
        "created_at": now,
        "updated_at": now,
    }
