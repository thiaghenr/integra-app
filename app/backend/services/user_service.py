from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.phone import canonical_phone
from app.backend.core.security import hash_password, verify_password
from app.backend.models.phone_list import PhoneList
from app.backend.models.user import User
from app.backend.repositories.phone_list_repository import PhoneListRepository
from app.backend.repositories.user_repository import UserRepository
from app.backend.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = UserRepository(session)
        self.phone_list_repo = PhoneListRepository(session)

    async def list(self, clinic_id: int | None) -> list[User]:
        return await self.repo.list_by_clinic(clinic_id)

    async def get(self, clinic_id: int | None, user_id: int) -> User:
        user = await self.repo.get(user_id)
        if not user or (clinic_id is not None and user.clinic_id != clinic_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def create(self, clinic_id: int, data: UserCreate, force_password_change: bool = False) -> User:
        existing = await self.repo.get_by_email(clinic_id, data.email)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
        user = User(
            clinic_id=clinic_id,
            email=data.email,
            name=data.name,
            surname=data.surname,
            role=data.role,
            password_hash=hash_password(data.password),
            force_password_change=force_password_change,
        )
        if data.phone:
            canonical = canonical_phone(data.phone)
            if await self.phone_list_repo.get_by_canonical(canonical):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Phone already associated with another user"
                )
        user = await self.repo.create(user)
        if data.phone:
            await self.phone_list_repo.create(
                PhoneList(user_id=user.id, phone=data.phone, phone_canonical=canonical)
            )
        return user

    async def update(self, clinic_id: int | None, user_id: int, data: UserUpdate) -> User:
        user = await self.get(clinic_id, user_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(user, field, value)
        return await self.repo.update(user)

    async def soft_delete(self, clinic_id: int | None, user_id: int) -> None:
        user = await self.get(clinic_id, user_id)
        user.is_active = False
        await self.repo.update(user)

    async def change_password(self, user: User, current_password: str, new_password: str) -> User:
        if not verify_password(current_password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password")
        user.password_hash = hash_password(new_password)
        user.force_password_change = False
        return await self.repo.update(user)
