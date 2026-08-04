from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException, Request, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.config import settings
from app.backend.core.database import AsyncSessionLocal
from app.backend.core.security import decode_jwt, decode_session_token
from app.backend.models.user import User, UserRole
from app.backend.repositories.user_repository import UserRepository


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(request: Request, session: AsyncSession = Depends(get_db)) -> User:
    user: User | None = getattr(request.state, "user", None)
    if user is not None:
        return user
    print("NO USER!!!")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def require_roles(*roles: UserRole):
    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == UserRole.superadmin:
            return current_user
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return dependency


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if not settings.CHATBOT_API_KEY or x_api_key != settings.CHATBOT_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")


def require_superadmin():
    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != UserRole.superadmin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")
        return current_user

    return dependency


def clinic_scope(user: User) -> int | None:
    """Returns None for superadmin (all clinics), the user's clinic_id otherwise."""
    return None if user.role == UserRole.superadmin else user.clinic_id


async def load_user_from_bearer(request: Request, session: AsyncSession) -> User | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        print("l59" * 2)
        return None
    token = auth.removeprefix("Bearer ")
    user_id = decode_jwt(token)
    if not user_id:
        print("l64" * 2)
        return None
    repo = UserRepository(session)
    user = await repo.get(user_id)
    if not user or not user.is_active:
        print("l69" * 2)
        return None
    return user


async def load_user_from_cookie(request: Request, session: AsyncSession) -> User | None:
    cookie_name = request.app.state.settings.SESSION_COOKIE_NAME
    token = request.cookies.get(cookie_name)
    if not token:
        return None
    user_id = decode_session_token(token)
    if not user_id:
        return None
    repo = UserRepository(session)
    user = await repo.get(user_id)
    if not user or not user.is_active:
        return None
    return user
