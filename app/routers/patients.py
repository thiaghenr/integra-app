from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import clinic_scope, get_current_user, get_db, require_roles
from app.backend.models.user import User, UserRole
from app.backend.repositories.appointment_repository import AppointmentRepository
from app.backend.repositories.check_in_repository import CheckInRepository
from app.backend.repositories.clinic_repository import ClinicRepository
from app.backend.repositories.medical_record_repository import MedicalRecordRepository
from app.backend.repositories.user_repository import UserRepository
from app.backend.schemas.patient import PatientCreate, PatientUpdate
from app.backend.services.check_in_service import CheckInService
from app.backend.services.patient_service import PatientService

router = APIRouter(prefix="/patients")


def _t(request: Request):
    return request.app.state.templates


@router.get("", response_class=HTMLResponse)
async def list_patients(
    request: Request,
    search: str = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = PatientService(session)
    patients = await service.list(clinic_scope(current_user), search=search)
    return _t(request).TemplateResponse(
        request, "patients/list.html", {"user": current_user, "patients": patients, "search": search}
    )


@router.get("/new", response_class=HTMLResponse)
async def new_patient_form(
    request: Request,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.receptionist)),
    session: AsyncSession = Depends(get_db),
):
    clinics = []
    if current_user.role == UserRole.superadmin:
        clinics = await ClinicRepository(session).list_all()
    users = await UserRepository(session).list_by_clinic(clinic_scope(current_user))
    return _t(request).TemplateResponse(
        request, "patients/create.html", {"user": current_user, "clinics": clinics, "users": users, "error": None}
    )


@router.post("/new", response_class=HTMLResponse)
async def create_patient(
    request: Request,
    name: str = Form(...),
    surname: str = Form(...),
    cpf: str = Form(None),
    date_of_birth: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
    address: str = Form(None),
    notes: str = Form(None),
    user_id: str = Form(None),
    clinic_id: int = Form(None),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.receptionist)),
    session: AsyncSession = Depends(get_db),
):
    from datetime import date

    service = PatientService(session)
    target_clinic_id = clinic_id if (current_user.role == UserRole.superadmin and clinic_id) else current_user.clinic_id
    try:
        dob = date.fromisoformat(date_of_birth) if date_of_birth else None
        data = PatientCreate(
            name=name,
            surname=surname,
            cpf=cpf or None,
            date_of_birth=dob,
            phone=phone or None,
            email=email or None,
            address=address or None,
            notes=notes or None,
            user_id=int(user_id) if user_id else None,
        )
        patient, generated_password = await service.create(target_clinic_id, data)
    except Exception as e:
        clinics = await ClinicRepository(session).list_all() if current_user.role == UserRole.superadmin else []
        users = await UserRepository(session).list_by_clinic(clinic_scope(current_user))
        return _t(request).TemplateResponse(
            request, "patients/create.html", {"user": current_user, "clinics": clinics, "users": users, "error": str(e)}
        )
    if generated_password:
        return _t(request).TemplateResponse(
            request,
            "patients/detail.html",
            {
                "user": current_user,
                "patient": patient,
                "appointments": [],
                "records": [],
                "check_ins": [],
                "emotions_by_check_in": {},
                "body_signals_by_check_in": {},
                "generated_password": generated_password,
            },
        )
    return RedirectResponse("/patients", status_code=302)


@router.get("/{patient_id}", response_class=HTMLResponse)
async def patient_detail(
    request: Request,
    patient_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = PatientService(session)
    patient = await service.get(scope, patient_id)

    appt_repo = AppointmentRepository(session)
    appointments = await appt_repo.list_by_clinic(scope, patient_id=patient_id)

    record_repo = MedicalRecordRepository(session)
    records = await record_repo.list_by_clinic(scope, patient_id=patient_id)

    check_ins = []
    emotions_by_check_in = {}
    body_signals_by_check_in = {}
    if current_user.role in (UserRole.superadmin, UserRole.admin):
        check_in_repo = CheckInRepository(session)
        check_ins = await check_in_repo.list_by_clinic(scope, patient_id=patient_id)
        check_in_service = CheckInService(session)
        emotions_by_check_in = await check_in_service.emotion_names_by_check_in(scope, check_ins)
        body_signals_by_check_in = await check_in_service.body_signal_names_by_check_in(scope, check_ins)

    return _t(request).TemplateResponse(
        request,
        "patients/detail.html",
        {
            "user": current_user,
            "patient": patient,
            "appointments": appointments,
            "records": records,
            "check_ins": check_ins,
            "emotions_by_check_in": emotions_by_check_in,
            "body_signals_by_check_in": body_signals_by_check_in,
        },
    )


@router.get("/{patient_id}/edit", response_class=HTMLResponse)
async def edit_patient_form(
    request: Request,
    patient_id: int,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.receptionist)),
    session: AsyncSession = Depends(get_db),
):
    service = PatientService(session)
    patient = await service.get(clinic_scope(current_user), patient_id)
    users = await UserRepository(session).list_by_clinic(clinic_scope(current_user))
    return _t(request).TemplateResponse(
        request, "patients/edit.html", {"user": current_user, "patient": patient, "users": users, "error": None}
    )


@router.post("/{patient_id}/edit", response_class=HTMLResponse)
async def update_patient(
    request: Request,
    patient_id: int,
    name: str = Form(...),
    surname: str = Form(...),
    cpf: str = Form(None),
    date_of_birth: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
    address: str = Form(None),
    notes: str = Form(None),
    user_id: str = Form(None),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.receptionist)),
    session: AsyncSession = Depends(get_db),
):
    from datetime import date

    scope = clinic_scope(current_user)
    service = PatientService(session)
    try:
        dob = date.fromisoformat(date_of_birth) if date_of_birth else None
        data = PatientUpdate(
            name=name,
            surname=surname,
            cpf=cpf or None,
            date_of_birth=dob,
            phone=phone or None,
            email=email or None,
            address=address or None,
            notes=notes or None,
            user_id=int(user_id) if user_id else None,
        )
        await service.update(scope, patient_id, data)
    except Exception as e:
        patient = await service.get(scope, patient_id)
        users = await UserRepository(session).list_by_clinic(scope)
        return _t(request).TemplateResponse(
            request, "patients/edit.html", {"user": current_user, "patient": patient, "users": users, "error": str(e)}
        )
    return RedirectResponse(f"/patients/{patient_id}", status_code=302)


@router.post("/{patient_id}/delete")
async def delete_patient(
    patient_id: int,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.receptionist)),
    session: AsyncSession = Depends(get_db),
):
    service = PatientService(session)
    await service.soft_delete(clinic_scope(current_user), patient_id)
    return RedirectResponse("/patients", status_code=302)
