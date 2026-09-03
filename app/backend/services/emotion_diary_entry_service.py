from __future__ import annotations

from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.emotion_diary_entry import EmotionDiaryEntry
from app.backend.models.patient import Patient
from app.backend.models.user import User, UserRole
from app.backend.repositories.appointment_repository import AppointmentRepository
from app.backend.repositories.emotion_diary_entry_repository import EmotionDiaryEntryRepository
from app.backend.repositories.patient_repository import PatientRepository
from app.backend.repositories.professional_repository import ProfessionalRepository
from app.backend.schemas.emotion_diary_entry import EMOTION_LABELS, EmotionDiaryEntryCreate

_ADMIN_ROLES = (UserRole.superadmin, UserRole.admin)


class EmotionDiaryEntryService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = EmotionDiaryEntryRepository(session)
        self.patient_repo = PatientRepository(session)
        self.prof_repo = ProfessionalRepository(session)
        self.appointment_repo = AppointmentRepository(session)

    async def _own_patient(self, current_user: User) -> Patient:
        patient = await self.patient_repo.get_by_user_id(current_user.id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No patient profile linked to this account"
            )
        return patient

    async def _own_patient_ids_for_professional(self, clinic_id: int | None, current_user: User) -> list[int]:
        professional = await self.prof_repo.get_by_user_id(current_user.id)
        if not professional:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No professional profile linked to this account"
            )
        appointments = await self.appointment_repo.list_by_clinic(clinic_id, professional_id=professional.id)
        return sorted({a.patient_id for a in appointments})

    async def get(self, clinic_id: int | None, entry_id: int, current_user: User) -> EmotionDiaryEntry:
        entry = await self.repo.get(entry_id)
        if not entry or (clinic_id is not None and entry.clinic_id != clinic_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
        if current_user.role in _ADMIN_ROLES:
            return entry
        if current_user.role == UserRole.professional:
            patient_ids = await self._own_patient_ids_for_professional(clinic_id, current_user)
            if entry.patient_id not in patient_ids:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
            return entry
        if current_user.role == UserRole.paciente:
            patient = await self._own_patient(current_user)
            if entry.patient_id != patient.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
            return entry
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    async def list(self, clinic_id: int | None, current_user: User) -> list[EmotionDiaryEntry]:
        if current_user.role in _ADMIN_ROLES:
            return await self.repo.list_by_clinic(clinic_id)
        if current_user.role == UserRole.professional:
            patient_ids = await self._own_patient_ids_for_professional(clinic_id, current_user)
            if not patient_ids:
                return []
            return await self.repo.list_by_clinic(clinic_id, patient_ids=patient_ids)
        if current_user.role == UserRole.paciente:
            patient = await self._own_patient(current_user)
            return await self.repo.list_by_clinic(clinic_id, patient_id=patient.id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    async def list_own_paginated(
        self, clinic_id: int | None, current_user: User, page: int = 1, page_size: int = 5
    ) -> tuple[list[EmotionDiaryEntry], int]:
        patient = await self._own_patient(current_user)
        total = await self.repo.count_by_clinic(clinic_id, patient_id=patient.id)
        entries = await self.repo.list_by_clinic(
            clinic_id, patient_id=patient.id, limit=page_size, offset=(page - 1) * page_size
        )
        return entries, total

    def emotion_labels_by_entry(self, entries: list[EmotionDiaryEntry]) -> dict[int, list[str]]:
        return {e.id: [label for field, label in EMOTION_LABELS.items() if getattr(e, field)] for e in entries}

    async def create(self, current_user: User, data: EmotionDiaryEntryCreate) -> EmotionDiaryEntry:
        patient: Patient
        if current_user.role == UserRole.paciente:
            patient = await self._own_patient(current_user)
        elif current_user.role == UserRole.superadmin:
            if not data.patient_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Paciente é obrigatório")
            found_patient = await self.patient_repo.get_by_clinic(None, data.patient_id)
            if not found_patient:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
            patient = found_patient
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        fields = data.model_dump(exclude={"patient_id"}, exclude_none=True)
        entry = EmotionDiaryEntry(clinic_id=patient.clinic_id, patient_id=patient.id, **fields)
        return await self.repo.create(entry)
