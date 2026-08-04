from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.goal import Goal
from app.backend.repositories.base import BaseRepository


class GoalRepository(BaseRepository[Goal]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Goal, session)

    async def list_by_clinic(
        self,
        clinic_id: int | None,
        professional_id: int | None = None,
        patient_id: int | None = None,
    ) -> list[Goal]:
        stmt = select(Goal).where(Goal.is_active == True)  # noqa: E712
        if clinic_id is not None:
            stmt = stmt.where(Goal.clinic_id == clinic_id)
        if professional_id:
            stmt = stmt.where(Goal.professional_id == professional_id)
        if patient_id:
            stmt = stmt.where(Goal.patient_id == patient_id)
        stmt = stmt.order_by(Goal.start_date.desc().nullslast(), Goal.created_at.desc())
        result = await self.session.exec(stmt)
        return list(result.all())

    async def get_by_clinic(self, clinic_id: int | None, goal_id: int) -> Goal | None:
        stmt = select(Goal).where(Goal.id == goal_id)
        if clinic_id is not None:
            stmt = stmt.where(Goal.clinic_id == clinic_id)
        result = await self.session.exec(stmt)
        return result.first()
