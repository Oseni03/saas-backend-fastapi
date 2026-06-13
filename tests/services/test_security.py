"""Unit tests for security utilities — no DB needed."""

import pytest
from jose import JWTError

from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_access_token,
    verify_password,
    verify_refresh_token,
    verify_token_hash,
)


def test_password_hash_and_verify() -> None:
    plain = "MySecurePass1!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("WrongPass1!", hashed)


def test_access_token_round_trip() -> None:
    user_id = "01HXYZ1234567890ABCDEFGHIJ"
    token = create_access_token(user_id)
    assert verify_access_token(token) == user_id


def test_refresh_token_round_trip() -> None:
    user_id = "01HXYZ1234567890ABCDEFGHIJ"
    token = create_refresh_token(user_id)
    assert verify_refresh_token(token) == user_id


def test_access_token_rejected_as_refresh() -> None:
    token = create_access_token("some-user-id")
    with pytest.raises(JWTError):
        verify_refresh_token(token)


def test_refresh_token_rejected_as_access() -> None:
    token = create_refresh_token("some-user-id")
    with pytest.raises(JWTError):
        verify_access_token(token)


def test_secure_token_uniqueness() -> None:
    tokens = {generate_secure_token() for _ in range(100)}
    assert len(tokens) == 100  # All unique


def test_token_hash_verify() -> None:
    raw = generate_secure_token()
    hashed = hash_token(raw)
    assert verify_token_hash(raw, hashed)
    assert not verify_token_hash("tampered", hashed)
