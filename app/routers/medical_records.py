from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import clinic_scope, get_db, require_roles
from app.backend.models.user import User, UserRole
from app.backend.repositories.patient_repository import PatientRepository
from app.backend.repositories.professional_repository import ProfessionalRepository
from app.backend.schemas.medical_record import MedicalRecordCreate, MedicalRecordUpdate
from app.backend.services.medical_record_service import MedicalRecordService

router = APIRouter(prefix="/medical-records")


def _t(request: Request):
    return request.app.state.templates


@router.get("", response_class=HTMLResponse)
async def list_records(
    request: Request,
    patient_id: int = Query(None),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = MedicalRecordService(session)
    records = await service.list(scope, current_user, patient_id=patient_id)

    patient_repo = PatientRepository(session)
    patient_map = {p.id: p for p in await patient_repo.list_by_clinic(scope)}

    prof_repo = ProfessionalRepository(session)
    prof_map = {p.id: p for p in await prof_repo.list_by_clinic(scope)}

    return _t(request).TemplateResponse(
        request,
        "medical_records/list.html",
        {"user": current_user, "records": records, "patient_map": patient_map, "prof_map": prof_map},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_record_form(
    request: Request,
    patient_id: int = Query(None),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    patient_repo = PatientRepository(session)
    patients = await patient_repo.list_by_clinic(clinic_scope(current_user))
    return _t(request).TemplateResponse(
        request,
        "medical_records/create.html",
        {"user": current_user, "patients": patients, "selected_patient_id": patient_id, "error": None},
    )


@router.post("/new", response_class=HTMLResponse)
async def create_record(
    request: Request,
    patient_id: int = Form(...),
    appointment_id: str = Form(None),
    title: str = Form(...),
    content: str = Form(...),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    service = MedicalRecordService(session)
    try:
        data = MedicalRecordCreate(
            patient_id=patient_id,
            appointment_id=int(appointment_id) if appointment_id else None,
            title=title,
            content=content,
        )
        await service.create(current_user.clinic_id, data, current_user)
    except Exception as e:
        patient_repo = PatientRepository(session)
        patients = await patient_repo.list_by_clinic(clinic_scope(current_user))
        return _t(request).TemplateResponse(
            request,
            "medical_records/create.html",
            {"user": current_user, "patients": patients, "selected_patient_id": patient_id, "error": str(e)},
        )
    return RedirectResponse("/medical-records", status_code=302)


@router.get("/{record_id}", response_class=HTMLResponse)
async def record_detail(
    request: Request,
    record_id: int,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = MedicalRecordService(session)
    record = await service.get(scope, record_id, current_user)

    patient_repo = PatientRepository(session)
    patient = await patient_repo.get_by_clinic(scope, record.patient_id)

    prof_repo = ProfessionalRepository(session)
    professional = await prof_repo.get(record.professional_id)

    return _t(request).TemplateResponse(
        request,
        "medical_records/detail.html",
        {"user": current_user, "record": record, "patient": patient, "professional": professional},
    )


@router.get("/{record_id}/edit", response_class=HTMLResponse)
async def edit_record_form(
    request: Request,
    record_id: int,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = MedicalRecordService(session)
    record = await service.get(scope, record_id, current_user)
    return _t(request).TemplateResponse(
        request, "medical_records/edit.html", {"user": current_user, "record": record, "error": None}
    )


@router.post("/{record_id}/edit", response_class=HTMLResponse)
async def update_record(
    request: Request,
    record_id: int,
    title: str = Form(...),
    content: str = Form(...),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = MedicalRecordService(session)
    try:
        data = MedicalRecordUpdate(title=title, content=content)
        await service.update(scope, record_id, data, current_user)
    except Exception as e:
        record = await service.get(scope, record_id, current_user)
        return _t(request).TemplateResponse(
            request,
            "medical_records/edit.html",
            {"user": current_user, "record": record, "error": str(e)},
        )
    return RedirectResponse(f"/medical-records/{record_id}", status_code=302)
