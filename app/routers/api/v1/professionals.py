from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import clinic_scope, get_current_user, get_db
from app.backend.models.user import User
from app.backend.repositories.professional_repository import ProfessionalRepository
from app.backend.schemas.patient import PatientRead
from app.backend.schemas.professional import ProfessionalRead
from app.backend.services.professional_service import ProfessionalService

router = APIRouter(tags=["professionals"])


@router.get("/professionals", response_model=list[ProfessionalRead])
async def api_list_professionals(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = ProfessionalService(session)
    return await service.list(clinic_scope(current_user))


@router.get("/professionals/me/patients", response_model=list[PatientRead])
async def api_list_my_patients(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    prof = await ProfessionalRepository(session).get_by_user_id(current_user.id)
    if not prof:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No professional profile linked to this account"
        )
    service = ProfessionalService(session)
    return await service.list_patients(clinic_scope(current_user), prof.id)


@router.get("/professionals/by-phone", response_model=ProfessionalRead)
async def api_get_professional_by_phone(
    phone: str = Query(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    professional = await ProfessionalRepository(session).get_by_phone(clinic_scope(current_user), phone)
    if not professional:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professional not found")
    return professional
