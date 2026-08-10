from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.google_docs import import_material_html
from app.backend.models.material import Material
from app.backend.models.patient import Patient
from app.backend.models.user import User, UserRole
from app.backend.repositories.material_repository import MaterialRepository
from app.backend.repositories.patient_repository import PatientRepository
from app.backend.schemas.material import MaterialImport


class MaterialService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = MaterialRepository(session)
        self.patient_repo = PatientRepository(session)

    async def _own_patient(self, current_user: User) -> Patient:
        patient = await self.patient_repo.get_by_user_id(current_user.id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No patient profile linked to this account"
            )
        return patient

    async def list(self, clinic_id: int | None, current_user: User) -> list[Material]:
        if current_user.role == UserRole.paciente:
            patient = await self._own_patient(current_user)
            return await self.repo.list_by_clinic(clinic_id, max_level=patient.level)
        return await self.repo.list_by_clinic(clinic_id)

    async def get(self, clinic_id: int | None, material_id: int, current_user: User) -> Material:
        material = await self.repo.get_by_clinic(clinic_id, material_id)
        if not material:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
        if current_user.role == UserRole.paciente:
            patient = await self._own_patient(current_user)
            if material.level > patient.level:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return material

    async def import_from_google_docs(self, clinic_id: int, data: MaterialImport, current_user: User) -> Material:
        doc_id, content_html = await import_material_html(data.source_url)
        material = Material(
            clinic_id=clinic_id,
            title=data.title,
            level=data.level,
            content_html=content_html,
            source_url=data.source_url,
            source_document_id=doc_id,
            imported_by=current_user.id,
        )
        return await self.repo.create(material)

    async def reimport(self, clinic_id: int | None, material_id: int, current_user: User) -> Material:
        # Reaproveita get() só pra achar/validar o material -- reimport é
        # sempre chamado por staff (role checada no router), então a checagem
        # de nível de paciente dentro de get() nunca dispara aqui na prática.
        material = await self.get(clinic_id, material_id, current_user)
        _, content_html = await import_material_html(material.source_url)
        material.content_html = content_html
        material.imported_at = datetime.utcnow()
        # current_user vem de get_current_user() -- é sempre um registro já
        # persistido, então .id nunca é None na prática. Mesmo quirk de
        # tipagem do SQLModel documentado no override de mypy pra services.
        material.imported_by = current_user.id  # type: ignore[assignment]
        material.updated_at = datetime.utcnow()
        return await self.repo.update(material)

    async def soft_delete(self, clinic_id: int | None, material_id: int, current_user: User) -> None:
        material = await self.get(clinic_id, material_id, current_user)
        material.is_active = False
        await self.repo.update(material)
