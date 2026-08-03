from __future__ import annotations

from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.check_in import CheckIn
from app.backend.models.patient import Patient
from app.backend.models.user import User, UserRole
from app.backend.repositories.body_signal_repository import BodySignalRepository
from app.backend.repositories.check_in_body_signal_repository import CheckInBodySignalRepository
from app.backend.repositories.check_in_emotion_repository import CheckInEmotionRepository
from app.backend.repositories.check_in_repository import CheckInRepository
from app.backend.repositories.emotion_repository import EmotionRepository
from app.backend.repositories.patient_repository import PatientRepository
from app.backend.schemas.check_in import CheckInCreate

_ADMIN_ROLES = (UserRole.superadmin, UserRole.admin)


class CheckInService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = CheckInRepository(session)
        self.patient_repo = PatientRepository(session)
        self.emotion_repo = EmotionRepository(session)
        self.check_in_emotion_repo = CheckInEmotionRepository(session)
        self.body_signal_repo = BodySignalRepository(session)
        self.check_in_body_signal_repo = CheckInBodySignalRepository(session)

    async def _own_patient(self, current_user: User) -> Patient:
        patient = await self.patient_repo.get_by_user_id(current_user.id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No patient profile linked to this account"
            )
        return patient

    async def get(self, clinic_id: int | None, check_in_id: int, current_user: User) -> CheckIn:
        check_in = await self.repo.get(check_in_id)
        if not check_in or (clinic_id is not None and check_in.clinic_id != clinic_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check-in not found")
        if current_user.role in _ADMIN_ROLES:
            return check_in
        if current_user.role == UserRole.paciente:
            patient = await self._own_patient(current_user)
            if check_in.patient_id != patient.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
            return check_in
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    async def list(self, clinic_id: int | None, current_user: User) -> list[CheckIn]:
        if current_user.role in _ADMIN_ROLES:
            return await self.repo.list_by_clinic(clinic_id)
        if current_user.role == UserRole.paciente:
            patient = await self._own_patient(current_user)
            return await self.repo.list_by_clinic(clinic_id, patient_id=patient.id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    async def create(self, current_user: User, data: CheckInCreate) -> CheckIn:
        if current_user.role == UserRole.paciente:
            patient = await self._own_patient(current_user)
        elif current_user.role == UserRole.superadmin:
            if not data.patient_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Paciente é obrigatório")
            patient = await self.patient_repo.get_by_clinic(None, data.patient_id)
            if not patient:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        valid_emotions = await self.emotion_repo.get_by_ids(patient.clinic_id, data.emotion_ids)
        if len(valid_emotions) != len(set(data.emotion_ids)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Emoção inválida")

        valid_body_signals = await self.body_signal_repo.get_by_ids(patient.clinic_id, data.body_signal_ids)
        if len(valid_body_signals) != len(set(data.body_signal_ids)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sinal corporal inválido")

        check_in = CheckIn(
            clinic_id=patient.clinic_id, patient_id=patient.id, intensity=data.intensity, notes=data.notes
        )
        check_in = await self.repo.create(check_in)
        await self.check_in_emotion_repo.create_many(check_in.id, [e.id for e in valid_emotions])
        await self.check_in_body_signal_repo.create_many(check_in.id, [b.id for b in valid_body_signals])
        return check_in

    async def emotion_names_by_check_in(self, clinic_id: int | None, check_ins: list[CheckIn]) -> dict[int, list[str]]:
        links = await self.check_in_emotion_repo.list_by_check_in_ids([c.id for c in check_ins])
        emotion_ids = sorted({link.emotion_id for link in links})
        emotions_by_id = {e.id: e for e in await self.emotion_repo.get_by_ids(clinic_id, emotion_ids)}

        grouped: dict[int, list[str]] = {}
        for link in links:
            emotion = emotions_by_id.get(link.emotion_id)
            if emotion:
                grouped.setdefault(link.check_in_id, []).append(emotion.name)
        return grouped

    async def body_signal_names_by_check_in(
        self, clinic_id: int | None, check_ins: list[CheckIn]
    ) -> dict[int, list[str]]:
        links = await self.check_in_body_signal_repo.list_by_check_in_ids([c.id for c in check_ins])
        body_signal_ids = sorted({link.body_signal_id for link in links})
        body_signals_by_id = {b.id: b for b in await self.body_signal_repo.get_by_ids(clinic_id, body_signal_ids)}

        grouped: dict[int, list[str]] = {}
        for link in links:
            body_signal = body_signals_by_id.get(link.body_signal_id)
            if body_signal:
                grouped.setdefault(link.check_in_id, []).append(body_signal.name)
        return grouped
