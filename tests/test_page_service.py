"""Unit tests for PageService.

File I/O (aiofiles, os) and the repository are fully mocked so no filesystem
or database access is required.
"""

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.page_service import PageService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_repo(
    *,
    page: dict | None = None,
    image_path: str | None = None,
    exists: bool = True,
    deleted: bool = True,
    updated_page: dict | None = None,
):
    repo = AsyncMock()
    repo.get_by_id.return_value = page
    repo.get_image_path.return_value = image_path
    repo.exists.return_value = exists
    repo.delete.return_value = deleted
    repo.update_status.return_value = updated_page
    repo.create.return_value = page or {}
    return repo


def make_page(page_id: uuid.UUID, user_id: uuid.UUID, status: str = "pending") -> dict:
    return {
        "id": page_id,
        "user_id": user_id,
        "image_path": f"{user_id}/test-image.jpg",
        "uploaded_date": date(2024, 1, 15),
        "page_start_date": None,
        "page_end_date": None,
        "notes": None,
        "page_status": status,
        "created_at": datetime.now(timezone.utc),
    }


def make_upload_file(filename: str = "photo.jpg", content: bytes = b"fake image data") -> MagicMock:
    """Return a mock that behaves like a FastAPI UploadFile."""
    mock = MagicMock()
    mock.filename = filename
    mock.read = AsyncMock(return_value=content)
    mock.seek = AsyncMock()
    return mock


def patch_file_io():
    """Patch all filesystem calls made inside page_service."""
    mock_file = AsyncMock()
    mock_file.write = AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_file)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)

    return (
        patch("app.services.page_service.aiofiles.open", return_value=mock_ctx),
        patch("app.services.page_service.os.makedirs"),
    )


# ---------------------------------------------------------------------------
# get_image_url
# ---------------------------------------------------------------------------

class TestGetImageUrl:
    def test_constructs_correct_url(self, user_id, page_id):
        service = PageService(make_repo())
        url = service.get_image_url(f"{user_id}/photo.jpg")
        assert url.startswith("http://")
        assert f"{user_id}/photo.jpg" in url

    def test_includes_uploads_path(self, user_id):
        service = PageService(make_repo())
        url = service.get_image_url("some/path.jpg")
        assert "/uploads/" in url


# ---------------------------------------------------------------------------
# get_page
# ---------------------------------------------------------------------------

class TestGetPage:
    async def test_returns_page_with_image_url(self, user_id, page_id):
        page = make_page(page_id, user_id)
        repo = make_repo(page=page)
        service = PageService(repo)

        result = await service.get_page(page_id, user_id)

        assert result["id"] == page_id
        assert "image_url" in result
        assert "image_path" not in result

    async def test_not_found_raises(self, user_id, page_id):
        repo = make_repo(page=None)
        service = PageService(repo)

        with pytest.raises(ValueError, match="Page not found"):
            await service.get_page(page_id, user_id)


# ---------------------------------------------------------------------------
# upload_page
# ---------------------------------------------------------------------------

class TestUploadPage:
    async def test_successful_upload(self, user_id, page_id):
        page = make_page(page_id, user_id)
        repo = make_repo(page=page)
        service = PageService(repo)
        upload = make_upload_file("photo.jpg")

        patch_open, patch_makedirs = patch_file_io()
        with patch_open, patch_makedirs:
            result = await service.upload_page(
                user_id=user_id,
                image=upload,
                uploaded_date=date(2024, 1, 15),
            )

        assert "image_url" in result
        repo.create.assert_awaited_once()

    @pytest.mark.parametrize("filename", ["photo.jpg", "scan.jpeg", "img.png", "anim.gif", "img.webp"])
    async def test_allowed_extensions(self, user_id, page_id, filename):
        page = make_page(page_id, user_id)
        repo = make_repo(page=page)
        service = PageService(repo)
        upload = make_upload_file(filename)

        patch_open, patch_makedirs = patch_file_io()
        with patch_open, patch_makedirs:
            result = await service.upload_page(user_id, upload, date(2024, 1, 15))

        assert "image_url" in result

    @pytest.mark.parametrize("filename", ["doc.pdf", "virus.exe", "data.csv", "archive.zip"])
    async def test_disallowed_extensions_raise(self, user_id, filename):
        service = PageService(make_repo())
        upload = make_upload_file(filename)

        with pytest.raises(ValueError, match="Invalid image format"):
            await service.upload_page(user_id, upload, date(2024, 1, 15))

    async def test_no_filename_raises(self, user_id):
        service = PageService(make_repo())
        upload = make_upload_file(filename=None)
        upload.filename = None

        with pytest.raises(ValueError, match="No image file provided"):
            await service.upload_page(user_id, upload, date(2024, 1, 15))

    async def test_file_too_large_raises(self, user_id):
        service = PageService(make_repo())
        # 11 MB — exceeds the 10 MB limit in settings
        oversized = b"x" * (11 * 1024 * 1024)
        upload = make_upload_file("photo.jpg", content=oversized)

        with pytest.raises(ValueError, match="File too large"):
            await service.upload_page(user_id, upload, date(2024, 1, 15))

    async def test_notes_are_forwarded_to_repository(self, user_id, page_id):
        page = make_page(page_id, user_id)
        repo = make_repo(page=page)
        service = PageService(repo)
        upload = make_upload_file()

        patch_open, patch_makedirs = patch_file_io()
        with patch_open, patch_makedirs:
            await service.upload_page(user_id, upload, date(2024, 1, 15), notes="My notes")

        _, kwargs = repo.create.call_args
        assert kwargs["notes"] == "My notes"


# ---------------------------------------------------------------------------
# delete_page
# ---------------------------------------------------------------------------

class TestDeletePage:
    async def test_successful_delete_removes_file(self, user_id, page_id):
        image_path = f"{user_id}/photo.jpg"
        repo = make_repo(image_path=image_path, deleted=True)
        service = PageService(repo)

        with patch("app.services.page_service.os.path.exists", return_value=True) as mock_exists, \
             patch("app.services.page_service.os.remove") as mock_remove:
            await service.delete_page(page_id, user_id)

        mock_remove.assert_called_once()
        repo.delete.assert_awaited_once_with(page_id, user_id)

    async def test_delete_skips_remove_when_file_missing(self, user_id, page_id):
        repo = make_repo(image_path=f"{user_id}/photo.jpg", deleted=True)
        service = PageService(repo)

        with patch("app.services.page_service.os.path.exists", return_value=False), \
             patch("app.services.page_service.os.remove") as mock_remove:
            await service.delete_page(page_id, user_id)

        mock_remove.assert_not_called()

    async def test_page_not_found_raises(self, user_id, page_id):
        repo = make_repo(image_path=None)
        service = PageService(repo)

        with pytest.raises(ValueError, match="Page not found"):
            await service.delete_page(page_id, user_id)

    async def test_repo_delete_failure_raises(self, user_id, page_id):
        repo = make_repo(image_path=f"{user_id}/photo.jpg", deleted=False)
        service = PageService(repo)

        with patch("app.services.page_service.os.path.exists", return_value=False):
            with pytest.raises(ValueError, match="Failed to delete page"):
                await service.delete_page(page_id, user_id)


# ---------------------------------------------------------------------------
# update_page_status
# ---------------------------------------------------------------------------

class TestUpdatePageStatus:
    async def test_successful_status_update(self, user_id, page_id):
        updated = make_page(page_id, user_id, status="transcribed")
        repo = make_repo(exists=True, updated_page=updated)
        service = PageService(repo)

        result = await service.update_page_status(page_id, user_id, "transcribed")

        assert result["page_status"] == "transcribed"
        assert "image_url" in result

    async def test_invalid_status_raises(self, user_id, page_id):
        service = PageService(make_repo())

        with pytest.raises(ValueError, match="Invalid page status"):
            await service.update_page_status(page_id, user_id, "invalid_status")

    async def test_page_not_found_raises(self, user_id, page_id):
        repo = make_repo(exists=False)
        service = PageService(repo)

        with pytest.raises(ValueError, match="Page not found"):
            await service.update_page_status(page_id, user_id, "transcribed")

    async def test_repo_returning_none_raises(self, user_id, page_id):
        repo = make_repo(exists=True, updated_page=None)
        service = PageService(repo)

        with pytest.raises(ValueError, match="Failed to update page"):
            await service.update_page_status(page_id, user_id, "transcribed")

    async def test_date_range_is_forwarded(self, user_id, page_id):
        updated = make_page(page_id, user_id, status="transcribed")
        repo = make_repo(exists=True, updated_page=updated)
        service = PageService(repo)
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)

        await service.update_page_status(
            page_id, user_id, "transcribed",
            page_start_date=start, page_end_date=end,
        )

        _, kwargs = repo.update_status.call_args
        assert kwargs["page_start_date"] == start
        assert kwargs["page_end_date"] == end

    @pytest.mark.parametrize("status", ["pending", "transcribed"])
    async def test_both_valid_statuses_accepted(self, user_id, page_id, status):
        page = make_page(page_id, user_id, status=status)
        repo = make_repo(exists=True, updated_page=page)
        service = PageService(repo)

        result = await service.update_page_status(page_id, user_id, status)

        assert result["page_status"] == status
