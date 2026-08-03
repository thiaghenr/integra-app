from datetime import date, datetime, time

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.appointment import Appointment, AppointmentStatus
from app.backend.repositories.base import BaseRepository


class AppointmentRepository(BaseRepository[Appointment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Appointment, session)

    async def list_by_clinic(
        self,
        clinic_id: int | None,
        professional_id: int | None = None,
        patient_id: int | None = None,
        date_filter: date | None = None,
    ) -> list[Appointment]:
        stmt = select(Appointment)
        if clinic_id is not None:
            stmt = stmt.where(Appointment.clinic_id == clinic_id)
        if professional_id:
            stmt = stmt.where(Appointment.professional_id == professional_id)
        if patient_id:
            stmt = stmt.where(Appointment.patient_id == patient_id)
        if date_filter:
            day_start = datetime.combine(date_filter, time.min)
            day_end = datetime.combine(date_filter, time.max)
            stmt = stmt.where(Appointment.scheduled_at >= day_start, Appointment.scheduled_at <= day_end)
        stmt = stmt.order_by(Appointment.scheduled_at)
        result = await self.session.exec(stmt)
        return list(result.all())

    async def list_today(self, clinic_id: int | None) -> list[Appointment]:
        return await self.list_by_clinic(clinic_id, date_filter=datetime.utcnow().date())

    async def get_by_clinic(self, clinic_id: int | None, appointment_id: int) -> Appointment | None:
        stmt = select(Appointment).where(Appointment.id == appointment_id)
        if clinic_id is not None:
            stmt = stmt.where(Appointment.clinic_id == clinic_id)
        result = await self.session.exec(stmt)
        return result.first()

    async def count_by_status(self, clinic_id: int | None) -> dict[str, int]:
        appointments = await self.list_by_clinic(clinic_id)
        counts: dict[str, int] = {s.value: 0 for s in AppointmentStatus}
        for appt in appointments:
            counts[appt.status.value] += 1
        return counts
