from datetime import date, datetime, time

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import clinic_scope, get_current_user, get_db, require_roles
from app.backend.models.user import User, UserRole
from app.backend.repositories.appointment_repository import AppointmentRepository
from app.backend.schemas.appointment import AppointmentCreate, AppointmentRead, AppointmentUpdate
from app.backend.services.appointment_service import AppointmentService

router = APIRouter(tags=["appointments"])


@router.get("/appointments", response_model=list[AppointmentRead])
async def api_list_appointments(
    professional_id: int = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AppointmentService(session)
    return await service.list(clinic_scope(current_user), current_user, professional_id=professional_id)


@router.post("/appointments", response_model=AppointmentRead)
async def api_create_appointment(
    data: AppointmentCreate,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.receptionist)),
    session: AsyncSession = Depends(get_db),
):
    service = AppointmentService(session)
    return await service.create(current_user.clinic_id, data, current_user)


@router.patch("/appointments/{appointment_id}", response_model=AppointmentRead)
async def api_update_appointment(
    appointment_id: int,
    data: AppointmentUpdate,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.receptionist)),
    session: AsyncSession = Depends(get_db),
):
    service = AppointmentService(session)
    return await service.update(clinic_scope(current_user), appointment_id, data, current_user)


@router.get("/appointments/availability", response_model=list[str])
async def api_availability(
    professional_id: int = Query(...),
    date_str: str = Query(..., alias="date"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = AppointmentRepository(session)
    target_date = date.fromisoformat(date_str)
    appointments = await repo.list_by_clinic(
        clinic_scope(current_user), professional_id=professional_id, date_filter=target_date
    )
    booked_slots = {a.scheduled_at.strftime("%H:%M") for a in appointments}
    all_slots = []
    slot = datetime.combine(target_date, time(8, 0))
    end = datetime.combine(target_date, time(18, 0))
    while slot < end:
        if slot.strftime("%H:%M") not in booked_slots:
            all_slots.append(slot.strftime("%H:%M"))
        slot = slot.replace(minute=slot.minute + 50 if slot.minute + 50 < 60 else 0,
                            hour=slot.hour + (slot.minute + 50) // 60)
    return all_slots
