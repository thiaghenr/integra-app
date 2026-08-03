from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import clinic_scope, get_current_user, get_db
from app.backend.models.user import User
from app.backend.repositories.professional_repository import ProfessionalRepository
from app.backend.schemas.bot import BotAppointmentRead, BotPatientRead, BotSlotRead
from app.backend.services.bot_service import BotService

router = APIRouter(tags=["bot"])


@router.get("/appointments", response_model=list[BotAppointmentRead])
async def bot_list_appointments(
    professional_id: int = Query(None),
    patient_id: int = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = BotService(session)
    return await service.list_appointments(
        clinic_scope(current_user), current_user, professional_id=professional_id, patient_id=patient_id
    )


@router.get("/appointments/availability", response_model=list[BotSlotRead])
async def bot_availability(
    professional_id: int = Query(...),
    date_str: str = Query(..., alias="date"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = BotService(session)
    target_date = date.fromisoformat(date_str)
    return await service.list_availability(clinic_scope(current_user), professional_id, target_date)


@router.get("/professionals/me/patients", response_model=list[BotPatientRead])
async def bot_list_my_patients(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    prof = await ProfessionalRepository(session).get_by_user_id(current_user.id)
    if not prof:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No professional profile linked to this account"
        )
    service = BotService(session)
    return await service.list_my_patients(clinic_scope(current_user), prof.id)
