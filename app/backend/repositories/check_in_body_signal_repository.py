from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.check_in_body_signal import CheckInBodySignal
from app.backend.repositories.base import BaseRepository


class CheckInBodySignalRepository(BaseRepository[CheckInBodySignal]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CheckInBodySignal, session)

    async def create_many(self, check_in_id: int, body_signal_ids: list[int]) -> None:
        for body_signal_id in body_signal_ids:
            self.session.add(CheckInBodySignal(check_in_id=check_in_id, body_signal_id=body_signal_id))
        if body_signal_ids:
            await self.session.commit()

    async def list_by_check_in_ids(self, check_in_ids: list[int]) -> list[CheckInBodySignal]:
        if not check_in_ids:
            return []
        stmt = select(CheckInBodySignal).where(CheckInBodySignal.check_in_id.in_(check_in_ids))
        result = await self.session.exec(stmt)
        return list(result.all())
