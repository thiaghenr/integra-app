from __future__ import annotations

from datetime import date, datetime, time

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.patient import Patient
from app.backend.models.user import User, UserRole
from app.backend.repositories.appointment_repository import AppointmentRepository
from app.backend.repositories.patient_repository import PatientRepository
from app.backend.repositories.professional_repository import ProfessionalRepository
from app.backend.schemas.bot import BotAppointmentRead, BotPatientRead, BotSlotRead
from app.backend.services.appointment_service import AppointmentService
from app.backend.services.professional_service import ProfessionalService

_UNKNOWN_PATIENT = "Paciente não encontrado"
_UNKNOWN_PROFESSIONAL = "Profissional não encontrado"


class BotService:
    """Enrichment layer for the WhatsApp chatbot's /api/v1/bot/ routes.

    Reuses existing repositories/services untouched and joins in extra
    display fields (names, phone, specialization) the chatbot needs in a
    single call.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.appointment_service = AppointmentService(session)
        self.professional_service = ProfessionalService(session)
        self.appointment_repo = AppointmentRepository(session)
        self.patient_repo = PatientRepository(session)
        self.professional_repo = ProfessionalRepository(session)

    async def _own_patient_id(self, user_id: int) -> int | None:
        result = await self.session.exec(
            select(Patient.id).where(Patient.user_id == user_id, Patient.is_active == True)  # noqa: E712
        )
        return result.first()

    async def list_appointments(
        self,
        clinic_id: int | None,
        current_user: User,
        professional_id: int | None = None,
        patient_id: int | None = None,
    ) -> list[BotAppointmentRead]:
        appointments = await self.appointment_service.list(clinic_id, current_user, professional_id=professional_id)

        if current_user.role == UserRole.paciente:
            own_patient_id = await self._own_patient_id(current_user.id)
            appointments = [a for a in appointments if a.patient_id == own_patient_id]
        elif patient_id is not None:
            appointments = [a for a in appointments if a.patient_id == patient_id]

        if not appointments:
            return []

        patient_ids = sorted({a.patient_id for a in appointments})
        patients_by_id = {p.id: p for p in await self.patient_repo.get_by_ids(clinic_id, patient_ids)}
        professionals_by_id = {
            p.id: p for p in await self.professional_repo.list_by_clinic(clinic_id, active_only=False)
        }

        enriched = []
        for a in appointments:
            patient = patients_by_id.get(a.patient_id)
            professional = professionals_by_id.get(a.professional_id)
            enriched.append(
                BotAppointmentRead(
                    id=a.id,
                    scheduled_at=a.scheduled_at,
                    duration_minutes=a.duration_minutes,
                    status=a.status.value,
                    notes=a.notes,
                    patient_name=patient.full_name if patient else _UNKNOWN_PATIENT,
                    patient_phone=patient.phone if patient else None,
                    professional_name=professional.full_name if professional else _UNKNOWN_PROFESSIONAL,
                    professional_specialization=professional.specialization if professional else None,
                )
            )
        return enriched

    async def list_availability(
        self, clinic_id: int | None, professional_id: int, target_date: date
    ) -> list[BotSlotRead]:
        professional = await self.professional_repo.get(professional_id)
        professional_name = professional.full_name if professional else _UNKNOWN_PROFESSIONAL

        appointments = await self.appointment_repo.list_by_clinic(
            clinic_id, professional_id=professional_id, date_filter=target_date
        )
        booked_slots = {a.scheduled_at.strftime("%H:%M") for a in appointments}

        slots = []
        slot = datetime.combine(target_date, time(8, 0))
        end = datetime.combine(target_date, time(18, 0))
        while slot < end:
            if slot.strftime("%H:%M") not in booked_slots:
                slots.append(
                    BotSlotRead(
                        time=slot.strftime("%H:%M"),
                        professional_name=professional_name,
                        professional_id=professional_id,
                    )
                )
            slot = slot.replace(
                minute=slot.minute + 50 if slot.minute + 50 < 60 else 0,
                hour=slot.hour + (slot.minute + 50) // 60,
            )
        return slots

    async def list_my_patients(self, clinic_id: int | None, professional_id: int) -> list[BotPatientRead]:
        patients = await self.professional_service.list_patients(clinic_id, professional_id)
        appointments = await self.appointment_repo.list_by_clinic(clinic_id, professional_id=professional_id)

        last_by_patient: dict[int, datetime] = {}
        for a in appointments:
            current = last_by_patient.get(a.patient_id)
            if current is None or a.scheduled_at > current:
                last_by_patient[a.patient_id] = a.scheduled_at

        return [
            BotPatientRead(
                id=p.id,
                full_name=p.full_name,
                phone=p.phone,
                last_appointment_at=last_by_patient.get(p.id),
            )
            for p in patients
        ]
