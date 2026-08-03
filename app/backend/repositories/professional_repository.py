from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.phone import phone_variants
from app.backend.models.professional import Professional
from app.backend.repositories.base import BaseRepository


class ProfessionalRepository(BaseRepository[Professional]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Professional, session)

    async def list_by_clinic(self, clinic_id: int | None, active_only: bool = True) -> list[Professional]:
        stmt = select(Professional)
        if clinic_id is not None:
            stmt = stmt.where(Professional.clinic_id == clinic_id)
        if active_only:
            stmt = stmt.where(Professional.is_active == True)  # noqa: E712
        stmt = stmt.order_by(Professional.name, Professional.surname)
        result = await self.session.exec(stmt)
        return list(result.all())

    async def get_by_user_id(self, user_id: int) -> Professional | None:
        result = await self.session.exec(
            select(Professional).where(Professional.user_id == user_id, Professional.is_active == True)  # noqa: E712
        )
        return result.first()

    async def get_by_phone(self, clinic_id: int | None, phone: str) -> Professional | None:
        stmt = select(Professional).where(
            Professional.phone.in_(phone_variants(phone)), Professional.is_active == True  # noqa: E712
        )
        if clinic_id is not None:
            stmt = stmt.where(Professional.clinic_id == clinic_id)
        result = await self.session.exec(stmt)
        return result.first()
