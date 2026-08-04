from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.mission import Mission
from app.backend.repositories.base import BaseRepository


class MissionRepository(BaseRepository[Mission]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Mission, session)

    async def list_by_clinic(
        self,
        clinic_id: int | None,
        professional_id: int | None = None,
        patient_id: int | None = None,
    ) -> list[Mission]:
        stmt = select(Mission).where(Mission.is_active == True)  # noqa: E712
        if clinic_id is not None:
            stmt = stmt.where(Mission.clinic_id == clinic_id)
        if professional_id:
            stmt = stmt.where(Mission.professional_id == professional_id)
        if patient_id:
            stmt = stmt.where(Mission.patient_id == patient_id)
        stmt = stmt.order_by(Mission.start_date.desc().nullslast(), Mission.created_at.desc())
        result = await self.session.exec(stmt)
        return list(result.all())

    async def get_by_clinic(self, clinic_id: int | None, mission_id: int) -> Mission | None:
        stmt = select(Mission).where(Mission.id == mission_id)
        if clinic_id is not None:
            stmt = stmt.where(Mission.clinic_id == clinic_id)
        result = await self.session.exec(stmt)
        return result.first()
