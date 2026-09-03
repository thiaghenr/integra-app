import math

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import clinic_scope, get_current_user, get_db
from app.backend.models.user import User, UserRole
from app.backend.repositories.patient_repository import PatientRepository
from app.backend.repositories.professional_repository import ProfessionalRepository
from app.backend.services.appointment_service import AppointmentService
from app.backend.services.check_in_service import CheckInService
from app.backend.services.emotion_diary_entry_service import EmotionDiaryEntryService
from app.backend.services.goal_service import GoalService
from app.backend.services.mission_service import MissionService

router = APIRouter()

CHECK_IN_PAGE_SIZE = 5
EMOTION_DIARY_PAGE_SIZE = 5


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    page: int = Query(1, ge=1),
    diary_page: int = Query(1, ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)

    if current_user.role == UserRole.paciente:
        return await _patient_dashboard(request, current_user, session, scope, page, diary_page)

    appt_service = AppointmentService(session)
    today_appointments = await appt_service.list_today(scope)
    status_counts = await appt_service.count_by_status(scope)

    patient_repo = PatientRepository(session)
    patients = await patient_repo.list_by_clinic(scope)
    total_patients = len(patients)

    prof_repo = ProfessionalRepository(session)
    professionals = await prof_repo.list_by_clinic(scope)
    total_professionals = len(professionals)

    return request.app.state.templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "user": current_user,
            "today_appointments": today_appointments,
            "status_counts": status_counts,
            "total_patients": total_patients,
            "total_professionals": total_professionals,
        },
    )


async def _patient_dashboard(
    request: Request, current_user: User, session: AsyncSession, scope: int | None, page: int, diary_page: int
) -> HTMLResponse:
    check_in_service = CheckInService(session)
    check_ins, total_check_ins = await check_in_service.list_own_paginated(
        scope, current_user, page=page, page_size=CHECK_IN_PAGE_SIZE
    )
    emotions_by_check_in = await check_in_service.emotion_names_by_check_in(scope, check_ins)
    body_signals_by_check_in = await check_in_service.body_signal_names_by_check_in(scope, check_ins)
    total_check_in_pages = max(1, math.ceil(total_check_ins / CHECK_IN_PAGE_SIZE))

    diary_service = EmotionDiaryEntryService(session)
    diary_entries, total_diary_entries = await diary_service.list_own_paginated(
        scope, current_user, page=diary_page, page_size=EMOTION_DIARY_PAGE_SIZE
    )
    emotions_by_diary_entry = diary_service.emotion_labels_by_entry(diary_entries)
    total_diary_pages = max(1, math.ceil(total_diary_entries / EMOTION_DIARY_PAGE_SIZE))

    goals = await GoalService(session).list(scope, current_user)
    missions = await MissionService(session).list(scope, current_user)
    appointments = await AppointmentService(session).list(scope, current_user)

    prof_map = {p.id: p for p in await ProfessionalRepository(session).list_by_clinic(scope)}

    return request.app.state.templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "user": current_user,
            "check_ins": check_ins,
            "emotions_by_check_in": emotions_by_check_in,
            "body_signals_by_check_in": body_signals_by_check_in,
            "check_in_page": page,
            "total_check_in_pages": total_check_in_pages,
            "diary_entries": diary_entries,
            "emotions_by_diary_entry": emotions_by_diary_entry,
            "diary_page": diary_page,
            "total_diary_pages": total_diary_pages,
            "goals": goals,
            "missions": missions,
            "appointments": appointments,
            "prof_map": prof_map,
        },
    )
