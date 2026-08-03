from datetime import datetime, timedelta, timezone

import jwt

from app.backend.core.config import settings
from app.backend.core.security import (
    create_jwt,
    create_session_token,
    decode_jwt,
    decode_session_token,
    hash_password,
    verify_password,
)


def test_hash_password_round_trip():
    hashed = hash_password("mysecret123")
    assert hashed != "mysecret123"
    assert verify_password("mysecret123", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("mysecret123")
    assert verify_password("wrongpassword", hashed) is False


def test_create_and_decode_jwt_round_trip():
    token = create_jwt(user_id=42)
    assert decode_jwt(token) == 42


def test_decode_jwt_rejects_expired_token():
    expired_payload = {"sub": "42", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}
    expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    assert decode_jwt(expired_token) is None


def test_decode_jwt_rejects_garbage_token():
    assert decode_jwt("not-a-valid-token") is None


def test_create_and_decode_session_token_round_trip():
    token = create_session_token(user_id=7)
    assert decode_session_token(token) == 7


def test_decode_session_token_rejects_tampered_token():
    token = create_session_token(user_id=7)
    mid = len(token) // 2
    tampered = token[:mid] + ("a" if token[mid] != "a" else "b") + token[mid + 1 :]
    assert decode_session_token(tampered) is None
