from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import clinic_scope, get_current_user, get_db, require_roles
from app.backend.models.appointment import AppointmentStatus
from app.backend.models.user import User, UserRole
from app.backend.repositories.patient_repository import PatientRepository
from app.backend.repositories.professional_repository import ProfessionalRepository
from app.backend.schemas.appointment import AppointmentCreate, AppointmentUpdate
from app.backend.services.appointment_service import AppointmentService

router = APIRouter(prefix="/appointments")


def _t(request: Request):
    return request.app.state.templates


@router.get("", response_class=HTMLResponse)
async def list_appointments(
    request: Request,
    professional_id: int = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = AppointmentService(session)
    appointments = await service.list(scope, current_user, professional_id=professional_id)

    prof_repo = ProfessionalRepository(session)
    professionals = await prof_repo.list_by_clinic(scope)

    patient_repo = PatientRepository(session)
    patient_map = {p.id: p for p in await patient_repo.list_by_clinic(scope)}
    prof_map = {p.id: p for p in professionals}

    return _t(request).TemplateResponse(
        request,
        "appointments/list.html",
        {
            "user": current_user,
            "appointments": appointments,
            "professionals": professionals,
            "patient_map": patient_map,
            "prof_map": prof_map,
            "selected_professional_id": professional_id,
            "AppointmentStatus": AppointmentStatus,
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def new_appointment_form(
    request: Request,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.receptionist, UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    prof_repo = ProfessionalRepository(session)
    professionals = await prof_repo.list_by_clinic(scope)
    patient_repo = PatientRepository(session)
    patients = await patient_repo.list_by_clinic(scope)
    own_professional_id = None
    error = None
    if current_user.role == UserRole.professional:
        own_prof = await prof_repo.get_by_user_id(current_user.id)
        own_professional_id = own_prof.id if own_prof else None
        if own_professional_id is None:
            error = "Nenhum perfil de profissional vinculado a esta conta."
    return _t(request).TemplateResponse(
        request,
        "appointments/create.html",
        {
            "user": current_user,
            "professionals": professionals,
            "patients": patients,
            "own_professional_id": own_professional_id,
            "error": error,
        },
    )


@router.post("/new", response_class=HTMLResponse)
async def create_appointment(
    request: Request,
    patient_id: int = Form(...),
    professional_id: int = Form(...),
    scheduled_at: str = Form(...),
    duration_minutes: int = Form(50),
    notes: str = Form(None),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.receptionist, UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    from datetime import datetime

    service = AppointmentService(session)
    try:
        data = AppointmentCreate(
            patient_id=patient_id,
            professional_id=professional_id,
            scheduled_at=datetime.fromisoformat(scheduled_at),
            duration_minutes=duration_minutes,
            notes=notes or None,
        )
        await service.create(current_user.clinic_id, data, current_user)
    except Exception as e:
        scope = clinic_scope(current_user)
        prof_repo = ProfessionalRepository(session)
        professionals = await prof_repo.list_by_clinic(scope)
        patient_repo = PatientRepository(session)
        patients = await patient_repo.list_by_clinic(scope)
        own_professional_id = None
        if current_user.role == UserRole.professional:
            own_prof = await prof_repo.get_by_user_id(current_user.id)
            own_professional_id = own_prof.id if own_prof else None
        return _t(request).TemplateResponse(
            request,
            "appointments/create.html",
            {
                "user": current_user,
                "professionals": professionals,
                "patients": patients,
                "own_professional_id": own_professional_id,
                "error": str(e),
            },
        )
    return RedirectResponse("/appointments", status_code=302)


@router.get("/{appointment_id}", response_class=HTMLResponse)
async def appointment_detail(
    request: Request,
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = AppointmentService(session)
    appointment = await service.get(scope, appointment_id, current_user)

    patient_repo = PatientRepository(session)
    patient = await patient_repo.get_by_clinic(scope, appointment.patient_id)

    prof_repo = ProfessionalRepository(session)
    professional = await prof_repo.get(appointment.professional_id)

    return _t(request).TemplateResponse(
        request,
        "appointments/detail.html",
        {
            "user": current_user,
            "appointment": appointment,
            "patient": patient,
            "professional": professional,
            "AppointmentStatus": AppointmentStatus,
        },
    )


@router.get("/{appointment_id}/edit", response_class=HTMLResponse)
async def edit_appointment_form(
    request: Request,
    appointment_id: int,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.receptionist, UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = AppointmentService(session)
    appointment = await service.get(scope, appointment_id, current_user)
    prof_repo = ProfessionalRepository(session)
    professionals = await prof_repo.list_by_clinic(scope)
    patient_repo = PatientRepository(session)
    patients = await patient_repo.list_by_clinic(scope)
    return _t(request).TemplateResponse(
        request,
        "appointments/edit.html",
        {
            "user": current_user,
            "appointment": appointment,
            "professionals": professionals,
            "patients": patients,
            "statuses": AppointmentStatus,
            "error": None,
        },
    )


@router.post("/{appointment_id}/edit", response_class=HTMLResponse)
async def update_appointment(
    request: Request,
    appointment_id: int,
    patient_id: int = Form(...),
    professional_id: int = Form(...),
    scheduled_at: str = Form(...),
    duration_minutes: int = Form(50),
    status: str = Form(...),
    notes: str = Form(None),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.receptionist, UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    from datetime import datetime

    scope = clinic_scope(current_user)
    service = AppointmentService(session)
    try:
        data = AppointmentUpdate(
            patient_id=patient_id,
            professional_id=professional_id,
            scheduled_at=datetime.fromisoformat(scheduled_at),
            duration_minutes=duration_minutes,
            status=AppointmentStatus(status),
            notes=notes or None,
        )
        await service.update(scope, appointment_id, data, current_user)
    except Exception as e:
        appointment = await service.get(scope, appointment_id, current_user)
        prof_repo = ProfessionalRepository(session)
        professionals = await prof_repo.list_by_clinic(scope)
        patient_repo = PatientRepository(session)
        patients = await patient_repo.list_by_clinic(scope)
        return _t(request).TemplateResponse(
            request,
            "appointments/edit.html",
            {
                "user": current_user,
                "appointment": appointment,
                "professionals": professionals,
                "patients": patients,
                "statuses": AppointmentStatus,
                "error": str(e),
            },
        )
    return RedirectResponse(f"/appointments/{appointment_id}", status_code=302)


@router.post("/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: int,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.receptionist, UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    service = AppointmentService(session)
    await service.cancel(clinic_scope(current_user), appointment_id, current_user)
    return RedirectResponse(f"/appointments/{appointment_id}", status_code=302)
