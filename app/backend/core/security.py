from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

from app.backend.core.config import settings

_signer = TimestampSigner(settings.SECRET_KEY)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_session_token(user_id: int) -> str:
    return _signer.sign(str(user_id)).decode()


def decode_session_token(token: str) -> int | None:
    try:
        value = _signer.unsign(token, max_age=settings.SESSION_MAX_AGE)
        return int(value.decode())
    except (BadSignature, SignatureExpired):
        return None


def create_jwt(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_jwt(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None
