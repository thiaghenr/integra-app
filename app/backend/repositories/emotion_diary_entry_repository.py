from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.emotion_diary_entry import EmotionDiaryEntry
from app.backend.repositories.base import BaseRepository


class EmotionDiaryEntryRepository(BaseRepository[EmotionDiaryEntry]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(EmotionDiaryEntry, session)

    async def list_by_clinic(
        self,
        clinic_id: int | None,
        patient_id: int | None = None,
        patient_ids: list[int] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[EmotionDiaryEntry]:
        stmt = select(EmotionDiaryEntry)
        if clinic_id is not None:
            stmt = stmt.where(EmotionDiaryEntry.clinic_id == clinic_id)
        if patient_id is not None:
            stmt = stmt.where(EmotionDiaryEntry.patient_id == patient_id)
        if patient_ids is not None:
            stmt = stmt.where(EmotionDiaryEntry.patient_id.in_(patient_ids))
        stmt = stmt.order_by(EmotionDiaryEntry.entry_date.desc())
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.exec(stmt)
        return list(result.all())

    async def count_by_clinic(self, clinic_id: int | None, patient_id: int | None = None) -> int:
        stmt = select(func.count()).select_from(EmotionDiaryEntry)
        if clinic_id is not None:
            stmt = stmt.where(EmotionDiaryEntry.clinic_id == clinic_id)
        if patient_id is not None:
            stmt = stmt.where(EmotionDiaryEntry.patient_id == patient_id)
        result = await self.session.exec(stmt)
        return result.one()
