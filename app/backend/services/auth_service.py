from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.security import verify_password
from app.backend.models.user import User
from app.backend.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = UserRepository(session)

    async def authenticate(self, clinic_id: int, email: str, password: str) -> User:
        user = await self.repo.get_by_email(clinic_id, email)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
        return user

    async def authenticate_global(self, email: str, password: str) -> User:
        user = await self.repo.get_by_email_global(email)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
        return user

    async def authenticate_by_phone(self, phone: str) -> User:
        user = await self.repo.get_by_phone(phone)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No user found for this phone number")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
        return user
