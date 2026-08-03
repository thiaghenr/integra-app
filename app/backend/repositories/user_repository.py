from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.phone import canonical_phone
from app.backend.models.phone_list import PhoneList
from app.backend.models.user import User
from app.backend.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, clinic_id: int, email: str) -> User | None:
        result = await self.session.exec(
            select(User).where(User.clinic_id == clinic_id, User.email == email)
        )
        return result.first()

    async def get_by_phone(self, phone: str) -> User | None:
        result = await self.session.exec(
            select(User)
            .join(PhoneList, PhoneList.user_id == User.id)
            .where(PhoneList.phone_canonical == canonical_phone(phone))
        )
        return result.first()

    async def get_by_email_global(self, email: str) -> User | None:
        result = await self.session.exec(select(User).where(User.email == email))
        return result.first()

    async def list_all(self) -> list[User]:
        result = await self.session.exec(select(User).order_by(User.name, User.surname))
        return list(result.all())

    async def list_by_clinic(self, clinic_id: int | None) -> list[User]:
        stmt = select(User).order_by(User.name, User.surname)
        if clinic_id is not None:
            stmt = stmt.where(User.clinic_id == clinic_id)
        result = await self.session.exec(stmt)
        return list(result.all())

