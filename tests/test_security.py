"""Unit tests for app/core/security.py.

All functions are pure (no DB or network calls), so no mocking is needed.
"""

import uuid
from datetime import timedelta

import pytest

from app.core.security import (
    create_jwt_token,
    decode_jwt_token,
    generate_salt,
    generate_session_token,
    get_user_id_from_token,
    hash_password,
    verify_password,
)


# ---------------------------------------------------------------------------
# generate_salt
# ---------------------------------------------------------------------------

class TestGenerateSalt:
    def test_returns_string(self):
        assert isinstance(generate_salt(), str)

    def test_length_is_64_hex_chars(self):
        # secrets.token_hex(32) → 64 hex characters
        assert len(generate_salt()) == 64

    def test_salts_are_unique(self):
        salts = {generate_salt() for _ in range(100)}
        assert len(salts) == 100


# ---------------------------------------------------------------------------
# hash_password / verify_password
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hash_is_not_plain_text(self):
        salt = generate_salt()
        hashed = hash_password("secret123", salt)
        assert "secret123" not in hashed

    def test_verify_correct_password(self):
        salt = generate_salt()
        hashed = hash_password("correctpassword", salt)
        assert verify_password("correctpassword", salt, hashed) is True

    def test_reject_wrong_password(self):
        salt = generate_salt()
        hashed = hash_password("correctpassword", salt)
        assert verify_password("wrongpassword", salt, hashed) is False

    def test_reject_wrong_salt(self):
        salt = generate_salt()
        hashed = hash_password("correctpassword", salt)
        different_salt = generate_salt()
        assert verify_password("correctpassword", different_salt, hashed) is False

    def test_same_password_different_salts_produce_different_hashes(self):
        salt1, salt2 = generate_salt(), generate_salt()
        hash1 = hash_password("password", salt1)
        hash2 = hash_password("password", salt2)
        assert hash1 != hash2


# ---------------------------------------------------------------------------
# create_jwt_token / decode_jwt_token
# ---------------------------------------------------------------------------

class TestJwtTokens:
    def test_create_returns_string(self):
        token = create_jwt_token(uuid.uuid4())
        assert isinstance(token, str)

    def test_decode_valid_token(self):
        user_id = uuid.uuid4()
        token = create_jwt_token(user_id)
        payload = decode_jwt_token(token)
        assert payload is not None
        assert payload["sub"] == str(user_id)

    def test_decode_contains_exp_and_iat(self):
        token = create_jwt_token(uuid.uuid4())
        payload = decode_jwt_token(token)
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_invalid_token_returns_none(self):
        assert decode_jwt_token("this.is.not.a.valid.token") is None

    def test_decode_tampered_token_returns_none(self):
        token = create_jwt_token(uuid.uuid4())
        tampered = token[:-5] + "XXXXX"
        assert decode_jwt_token(tampered) is None

    def test_decode_expired_token_returns_none(self):
        token = create_jwt_token(uuid.uuid4(), expires_delta=timedelta(seconds=-1))
        assert decode_jwt_token(token) is None

    def test_custom_expiry_is_honoured(self):
        token = create_jwt_token(uuid.uuid4(), expires_delta=timedelta(hours=1))
        payload = decode_jwt_token(token)
        assert payload is not None


# ---------------------------------------------------------------------------
# get_user_id_from_token
# ---------------------------------------------------------------------------

class TestGetUserIdFromToken:
    def test_returns_correct_uuid(self):
        user_id = uuid.uuid4()
        token = create_jwt_token(user_id)
        assert get_user_id_from_token(token) == user_id

    def test_invalid_token_returns_none(self):
        assert get_user_id_from_token("bad.token") is None

    def test_expired_token_returns_none(self):
        token = create_jwt_token(uuid.uuid4(), expires_delta=timedelta(seconds=-1))
        assert get_user_id_from_token(token) is None


# ---------------------------------------------------------------------------
# generate_session_token
# ---------------------------------------------------------------------------

class TestGenerateSessionToken:
    def test_returns_string(self):
        assert isinstance(generate_session_token(), str)

    def test_tokens_are_unique(self):
        tokens = {generate_session_token() for _ in range(100)}
        assert len(tokens) == 100

    def test_token_is_url_safe(self):
        token = generate_session_token()
        # URL-safe base64 uses only A-Z, a-z, 0-9, -, _
        import re
        assert re.fullmatch(r"[A-Za-z0-9\-_]+", token)
