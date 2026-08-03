from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.clinic import Clinic
from app.backend.repositories.base import BaseRepository


class ClinicRepository(BaseRepository[Clinic]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Clinic, session)

    async def get_by_slug(self, slug: str) -> Clinic | None:
        result = await self.session.exec(select(Clinic).where(Clinic.slug == slug))
        return result.first()

    async def list_all(self) -> list[Clinic]:
        result = await self.session.exec(select(Clinic).order_by(Clinic.name))
        return list(result.all())
