"""Unit tests for EntryService.

The repository is fully mocked so no database is required.
"""

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.services.entry_service import EntryService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_repo(
    *,
    entry: dict | None = None,
    entries: list[dict] | None = None,
    total: int = 0,
    exists: bool = True,
    deleted: bool = True,
    updated_entry: dict | None = None,
):
    repo = AsyncMock()
    repo.get_by_id.return_value = entry
    repo.get_all.return_value = (entries or [], total)
    repo.exists.return_value = exists
    repo.delete.return_value = deleted
    repo.update.return_value = updated_entry
    return repo


def make_entry(entry_id: uuid.UUID, user_id: uuid.UUID, page_id: uuid.UUID) -> dict:
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


# ---------------------------------------------------------------------------
# get_entries – pagination clamping
# ---------------------------------------------------------------------------

class TestGetEntries:
    async def test_returns_transformed_entries(self, user_id, entry_id, page_id):
        entry = make_entry(entry_id, user_id, page_id)
        repo = make_repo(entries=[entry], total=1)
        service = EntryService(repo)

        results, total = await service.get_entries(user_id)

        assert total == 1
        assert len(results) == 1
        assert results[0]["status"] == "transcribed"
        assert results[0]["id"] == entry_id

    async def test_page_below_one_is_clamped(self, user_id):
        repo = make_repo(entries=[], total=0)
        service = EntryService(repo)

        await service.get_entries(user_id, page=0)

        _, kwargs = repo.get_all.call_args
        assert kwargs["page"] == 1

    async def test_limit_below_one_is_clamped(self, user_id):
        repo = make_repo(entries=[], total=0)
        service = EntryService(repo)

        await service.get_entries(user_id, limit=0)

        _, kwargs = repo.get_all.call_args
        assert kwargs["limit"] == 1

    async def test_limit_above_100_is_clamped(self, user_id):
        repo = make_repo(entries=[], total=0)
        service = EntryService(repo)

        await service.get_entries(user_id, limit=999)

        _, kwargs = repo.get_all.call_args
        assert kwargs["limit"] == 100

    async def test_date_filters_are_passed_through(self, user_id):
        repo = make_repo(entries=[], total=0)
        service = EntryService(repo)
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)

        await service.get_entries(user_id, start_date=start, end_date=end)

        _, kwargs = repo.get_all.call_args
        assert kwargs["start_date"] == start
        assert kwargs["end_date"] == end

    async def test_empty_result(self, user_id):
        repo = make_repo(entries=[], total=0)
        service = EntryService(repo)
        results, total = await service.get_entries(user_id)
        assert results == []
        assert total == 0


# ---------------------------------------------------------------------------
# get_entry
# ---------------------------------------------------------------------------

class TestGetEntry:
    async def test_returns_entry_with_status(self, user_id, entry_id, page_id):
        entry = make_entry(entry_id, user_id, page_id)
        repo = make_repo(entry=entry)
        service = EntryService(repo)

        result = await service.get_entry(entry_id, user_id)

        assert result["id"] == entry_id
        assert result["status"] == "transcribed"
        assert result["raw_ocr_transcription"] == "Today was a good day."

    async def test_not_found_raises(self, user_id, entry_id):
        repo = make_repo(entry=None)
        service = EntryService(repo)

        with pytest.raises(ValueError, match="Entry not found"):
            await service.get_entry(entry_id, user_id)


# ---------------------------------------------------------------------------
# update_entry
# ---------------------------------------------------------------------------

class TestUpdateEntry:
    async def test_successful_update(self, user_id, entry_id, page_id):
        original = make_entry(entry_id, user_id, page_id)
        updated = {**original, "raw_ocr_transcription": "Updated text."}
        repo = make_repo(exists=True, updated_entry=updated)
        service = EntryService(repo)

        result = await service.update_entry(
            entry_id, user_id, raw_ocr_transcription="Updated text."
        )

        assert result["raw_ocr_transcription"] == "Updated text."
        assert result["status"] == "transcribed"

    async def test_not_found_raises(self, user_id, entry_id):
        repo = make_repo(exists=False)
        service = EntryService(repo)

        with pytest.raises(ValueError, match="Entry not found"):
            await service.update_entry(entry_id, user_id, raw_ocr_transcription="x")

    async def test_repo_returning_none_raises(self, user_id, entry_id):
        repo = make_repo(exists=True, updated_entry=None)
        service = EntryService(repo)

        with pytest.raises(ValueError, match="Failed to update entry"):
            await service.update_entry(entry_id, user_id, raw_ocr_transcription="x")

    async def test_partial_update_with_date_only(self, user_id, entry_id, page_id):
        original = make_entry(entry_id, user_id, page_id)
        new_date = date(2024, 2, 1)
        updated = {**original, "entry_date": new_date}
        repo = make_repo(exists=True, updated_entry=updated)
        service = EntryService(repo)

        result = await service.update_entry(entry_id, user_id, entry_date=new_date)

        assert result["entry_date"] == new_date


# ---------------------------------------------------------------------------
# delete_entry
# ---------------------------------------------------------------------------

class TestDeleteEntry:
    async def test_successful_delete(self, user_id, entry_id):
        repo = make_repo(exists=True, deleted=True)
        service = EntryService(repo)

        await service.delete_entry(entry_id, user_id)

        repo.delete.assert_awaited_once_with(entry_id, user_id)

    async def test_not_found_raises(self, user_id, entry_id):
        repo = make_repo(exists=False)
        service = EntryService(repo)

        with pytest.raises(ValueError, match="Entry not found"):
            await service.delete_entry(entry_id, user_id)

    async def test_repo_delete_failure_raises(self, user_id, entry_id):
        repo = make_repo(exists=True, deleted=False)
        service = EntryService(repo)

        with pytest.raises(ValueError, match="Failed to delete entry"):
            await service.delete_entry(entry_id, user_id)
