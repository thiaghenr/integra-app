from __future__ import annotations

from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.body_signal import BodySignal
from app.backend.repositories.body_signal_repository import BodySignalRepository
from app.backend.schemas.body_signal import BodySignalCreate


class BodySignalService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = BodySignalRepository(session)

    async def list(self, clinic_id: int | None, active_only: bool = False) -> list[BodySignal]:
        return await self.repo.list_by_clinic(clinic_id, active_only=active_only)

    async def create(self, clinic_id: int, data: BodySignalCreate) -> BodySignal:
        body_signal = BodySignal(clinic_id=clinic_id, category=data.category, name=data.name)
        return await self.repo.create(body_signal)

    async def soft_delete(self, clinic_id: int | None, body_signal_id: int) -> None:
        body_signal = await self.repo.get(body_signal_id)
        if body_signal and (clinic_id is None or body_signal.clinic_id == clinic_id):
            body_signal.is_active = False
            await self.repo.update(body_signal)
