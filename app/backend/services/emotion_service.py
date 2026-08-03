from __future__ import annotations

from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.emotion import Emotion
from app.backend.repositories.emotion_repository import EmotionRepository
from app.backend.schemas.emotion import EmotionCreate


class EmotionService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = EmotionRepository(session)

    async def list(self, clinic_id: int | None, active_only: bool = False) -> list[Emotion]:
        return await self.repo.list_by_clinic(clinic_id, active_only=active_only)

    async def create(self, clinic_id: int, data: EmotionCreate) -> Emotion:
        emotion = Emotion(clinic_id=clinic_id, name=data.name)
        return await self.repo.create(emotion)

    async def soft_delete(self, clinic_id: int | None, emotion_id: int) -> None:
        emotion = await self.repo.get(emotion_id)
        if emotion and (clinic_id is None or emotion.clinic_id == clinic_id):
            emotion.is_active = False
            await self.repo.update(emotion)
