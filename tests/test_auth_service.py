"""Unit tests for AuthService.

The repository is fully mocked so no database is required.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.services.auth_service import AuthService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_repo(
    *,
    email_exists: bool = False,
    username_exists: bool = False,
    created_user: dict | None = None,
    found_user: dict | None = None,
):
    """Build a mock IUserRepository with configurable behaviour."""
    repo = AsyncMock()
    repo.email_exists.return_value = email_exists
    repo.username_exists.return_value = username_exists
    repo.create.return_value = created_user or {}
    repo.get_by_email.return_value = found_user
    repo.get_by_id.return_value = found_user
    return repo


def make_user(user_id: uuid.UUID, *, password: str = "password123") -> dict:
    from app.core.security import generate_salt, hash_password
    salt = generate_salt()
    return {
        "id": user_id,
        "email": "test@example.com",
        "username": "testuser",
        "password_hash": hash_password(password, salt),
        "salt": salt,
        "created_at": datetime.now(timezone.utc),
    }


# ---------------------------------------------------------------------------
# validate_email
# ---------------------------------------------------------------------------

class TestValidateEmail:
    @pytest.fixture
    def service(self):
        return AuthService(make_repo())

    @pytest.mark.parametrize("email", [
        "user@example.com",
        "user.name+tag@sub.domain.org",
        "a@b.io",
    ])
    async def test_valid_emails(self, service, email):
        assert await service.validate_email(email) is True

    @pytest.mark.parametrize("email", [
        "notanemail",
        "@nodomain.com",
        "missing@",
        "spaces in@email.com",
        "",
    ])
    async def test_invalid_emails(self, service, email):
        assert await service.validate_email(email) is False


# ---------------------------------------------------------------------------
# validate_password
# ---------------------------------------------------------------------------

class TestValidatePassword:
    @pytest.fixture
    def service(self):
        return AuthService(make_repo())

    async def test_password_meeting_minimum_length(self, service):
        assert await service.validate_password("12345678") is True

    async def test_long_password(self, service):
        assert await service.validate_password("a" * 64) is True

    async def test_password_too_short(self, service):
        assert await service.validate_password("short") is False

    async def test_empty_password(self, service):
        assert await service.validate_password("") is False


# ---------------------------------------------------------------------------
# register
# ---------------------------------------------------------------------------

class TestRegister:
    async def test_successful_registration(self, user_id):
        user = make_user(user_id)
        repo = make_repo(created_user=user)
        service = AuthService(repo)

        result_user, token = await service.register(
            email="test@example.com",
            username="testuser",
            password="password123",
        )

        assert result_user["email"] == "test@example.com"
        assert result_user["username"] == "testuser"
        assert "password_hash" not in result_user
        assert "salt" not in result_user
        assert isinstance(token, str)
        repo.create.assert_awaited_once()

    async def test_invalid_email_raises(self, user_id):
        service = AuthService(make_repo())
        with pytest.raises(ValueError, match="Invalid email format"):
            await service.register("bademail", "user", "password123")

    async def test_short_password_raises(self, user_id):
        service = AuthService(make_repo())
        with pytest.raises(ValueError, match="8 characters"):
            await service.register("user@example.com", "user", "short")

    async def test_short_username_raises(self, user_id):
        service = AuthService(make_repo())
        with pytest.raises(ValueError, match="3 characters"):
            await service.register("user@example.com", "ab", "password123")

    async def test_duplicate_email_raises(self, user_id):
        repo = make_repo(email_exists=True)
        service = AuthService(repo)
        with pytest.raises(ValueError, match="Email already registered"):
            await service.register("user@example.com", "newuser", "password123")

    async def test_duplicate_username_raises(self, user_id):
        repo = make_repo(username_exists=True)
        service = AuthService(repo)
        with pytest.raises(ValueError, match="Username already taken"):
            await service.register("user@example.com", "takenuser", "password123")


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------

class TestLogin:
    async def test_successful_login(self, user_id):
        password = "correctpassword"
        user = make_user(user_id, password=password)
        repo = make_repo(found_user=user)
        service = AuthService(repo)

        result_user, token = await service.login(
            email="test@example.com",
            password=password,
        )

        assert result_user["id"] == user_id
        assert "password_hash" not in result_user
        assert "salt" not in result_user
        assert isinstance(token, str)

    async def test_wrong_email_raises(self):
        repo = make_repo(found_user=None)
        service = AuthService(repo)
        with pytest.raises(ValueError, match="Invalid email or password"):
            await service.login("nobody@example.com", "password123")

    async def test_wrong_password_raises(self, user_id):
        user = make_user(user_id, password="correctpassword")
        repo = make_repo(found_user=user)
        service = AuthService(repo)
        with pytest.raises(ValueError, match="Invalid email or password"):
            await service.login("test@example.com", "wrongpassword")

    async def test_error_message_does_not_distinguish_email_vs_password(self, user_id):
        """Prevents email enumeration: both wrong-email and wrong-password give the same message."""
        user = make_user(user_id, password="correctpassword")
        repo_no_user = make_repo(found_user=None)
        repo_wrong_pw = make_repo(found_user=user)
        service_no_user = AuthService(repo_no_user)
        service_wrong_pw = AuthService(repo_wrong_pw)

        with pytest.raises(ValueError) as exc_no_user:
            await service_no_user.login("nobody@example.com", "any")
        with pytest.raises(ValueError) as exc_wrong_pw:
            await service_wrong_pw.login("test@example.com", "wrongpassword")

        assert str(exc_no_user.value) == str(exc_wrong_pw.value)


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------

class TestGetCurrentUser:
    async def test_returns_user_without_sensitive_fields(self, user_id):
        user = make_user(user_id)
        repo = make_repo(found_user=user)
        service = AuthService(repo)

        result = await service.get_current_user(user_id)

        assert result is not None
        assert result["id"] == user_id
        assert "password_hash" not in result
        assert "salt" not in result

    async def test_returns_none_when_user_not_found(self, user_id):
        repo = make_repo(found_user=None)
        service = AuthService(repo)
        assert await service.get_current_user(user_id) is None


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------

class TestLogout:
    async def test_logout_is_a_noop(self):
        """JWT logout is stateless; the method should complete without error."""
        service = AuthService(make_repo())
        await service.logout("any-token")
