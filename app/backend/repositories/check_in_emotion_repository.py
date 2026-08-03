from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.check_in_emotion import CheckInEmotion
from app.backend.repositories.base import BaseRepository


class CheckInEmotionRepository(BaseRepository[CheckInEmotion]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CheckInEmotion, session)

    async def create_many(self, check_in_id: int, emotion_ids: list[int]) -> None:
        for emotion_id in emotion_ids:
            self.session.add(CheckInEmotion(check_in_id=check_in_id, emotion_id=emotion_id))
        if emotion_ids:
            await self.session.commit()

    async def list_by_check_in_ids(self, check_in_ids: list[int]) -> list[CheckInEmotion]:
        if not check_in_ids:
            return []
        stmt = select(CheckInEmotion).where(CheckInEmotion.check_in_id.in_(check_in_ids))
        result = await self.session.exec(stmt)
        return list(result.all())
