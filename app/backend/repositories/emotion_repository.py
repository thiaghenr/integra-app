from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.emotion import Emotion
from app.backend.repositories.base import BaseRepository


class EmotionRepository(BaseRepository[Emotion]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Emotion, session)

    async def list_by_clinic(self, clinic_id: int | None, active_only: bool = True) -> list[Emotion]:
        stmt = select(Emotion)
        if clinic_id is not None:
            stmt = stmt.where(Emotion.clinic_id == clinic_id)
        if active_only:
            stmt = stmt.where(Emotion.is_active == True)  # noqa: E712
        stmt = stmt.order_by(Emotion.name)
        result = await self.session.exec(stmt)
        return list(result.all())

    async def get_by_ids(self, clinic_id: int | None, emotion_ids: list[int]) -> list[Emotion]:
        if not emotion_ids:
            return []
        stmt = select(Emotion).where(Emotion.id.in_(emotion_ids))
        if clinic_id is not None:
            stmt = stmt.where(Emotion.clinic_id == clinic_id)
        stmt = stmt.order_by(Emotion.name)
        result = await self.session.exec(stmt)
        return list(result.all())
