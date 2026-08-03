from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import clinic_scope, get_current_user, get_db
from app.backend.models.user import User
from app.backend.repositories.patient_repository import PatientRepository
from app.backend.repositories.professional_repository import ProfessionalRepository
from app.backend.services.appointment_service import AppointmentService

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
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
