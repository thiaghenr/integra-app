from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.body_signal import BodySignal
from app.backend.repositories.base import BaseRepository


class BodySignalRepository(BaseRepository[BodySignal]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(BodySignal, session)

    async def list_by_clinic(self, clinic_id: int | None, active_only: bool = True) -> list[BodySignal]:
        stmt = select(BodySignal)
        if clinic_id is not None:
            stmt = stmt.where(BodySignal.clinic_id == clinic_id)
        if active_only:
            stmt = stmt.where(BodySignal.is_active == True)  # noqa: E712
        stmt = stmt.order_by(BodySignal.category, BodySignal.name)
        result = await self.session.exec(stmt)
        return list(result.all())

    async def get_by_ids(self, clinic_id: int | None, body_signal_ids: list[int]) -> list[BodySignal]:
        if not body_signal_ids:
            return []
        stmt = select(BodySignal).where(BodySignal.id.in_(body_signal_ids))
        if clinic_id is not None:
            stmt = stmt.where(BodySignal.clinic_id == clinic_id)
        stmt = stmt.order_by(BodySignal.category, BodySignal.name)
        result = await self.session.exec(stmt)
        return list(result.all())
