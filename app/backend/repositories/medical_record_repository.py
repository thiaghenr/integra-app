from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.medical_record import MedicalRecord
from app.backend.repositories.base import BaseRepository


class MedicalRecordRepository(BaseRepository[MedicalRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(MedicalRecord, session)

    async def list_by_clinic(
        self,
        clinic_id: int | None,
        professional_id: int | None = None,
        patient_id: int | None = None,
    ) -> list[MedicalRecord]:
        stmt = select(MedicalRecord)
        if clinic_id is not None:
            stmt = stmt.where(MedicalRecord.clinic_id == clinic_id)
        if professional_id:
            stmt = stmt.where(MedicalRecord.professional_id == professional_id)
        if patient_id:
            stmt = stmt.where(MedicalRecord.patient_id == patient_id)
        stmt = stmt.order_by(MedicalRecord.record_date.desc())
        result = await self.session.exec(stmt)
        return list(result.all())

    async def get_by_clinic(self, clinic_id: int | None, record_id: int) -> MedicalRecord | None:
        stmt = select(MedicalRecord).where(MedicalRecord.id == record_id)
        if clinic_id is not None:
            stmt = stmt.where(MedicalRecord.clinic_id == clinic_id)
        result = await self.session.exec(stmt)
        return result.first()
