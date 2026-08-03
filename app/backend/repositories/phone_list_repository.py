from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.phone_list import PhoneList
from app.backend.repositories.base import BaseRepository


class PhoneListRepository(BaseRepository[PhoneList]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(PhoneList, session)

    async def get_by_canonical(self, phone_canonical: str) -> PhoneList | None:
        result = await self.session.exec(
            select(PhoneList).where(PhoneList.phone_canonical == phone_canonical)
        )
        return result.first()
