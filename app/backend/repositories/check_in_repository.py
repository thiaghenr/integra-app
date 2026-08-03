from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.check_in import CheckIn
from app.backend.repositories.base import BaseRepository


class CheckInRepository(BaseRepository[CheckIn]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CheckIn, session)

    async def list_by_clinic(self, clinic_id: int | None, patient_id: int | None = None) -> list[CheckIn]:
        stmt = select(CheckIn)
        if clinic_id is not None:
            stmt = stmt.where(CheckIn.clinic_id == clinic_id)
        if patient_id is not None:
            stmt = stmt.where(CheckIn.patient_id == patient_id)
        stmt = stmt.order_by(CheckIn.checked_in_at.desc())
        result = await self.session.exec(stmt)
        return list(result.all())
