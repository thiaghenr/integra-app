from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import clinic_scope, get_current_user, get_db
from app.backend.models.user import User
from app.backend.repositories.patient_repository import PatientRepository
from app.backend.schemas.patient import PatientRead
from app.backend.services.patient_service import PatientService

router = APIRouter(tags=["patients"])


@router.get("/patients", response_model=list[PatientRead])
async def api_list_patients(
    search: str = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = PatientService(session)
    return await service.list(clinic_scope(current_user), search=search)


@router.get("/patients/by-phone", response_model=PatientRead)
async def api_get_patient_by_phone(
    phone: str = Query(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    patient = await PatientRepository(session).get_by_phone(clinic_scope(current_user), phone)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


@router.get("/patients/{patient_id}", response_model=PatientRead)
async def api_get_patient(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = PatientService(session)
    return await service.get(clinic_scope(current_user), patient_id)
