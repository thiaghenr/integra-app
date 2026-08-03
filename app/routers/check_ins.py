from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import clinic_scope, get_current_user, get_db, require_roles
from app.backend.models.user import User, UserRole
from app.backend.repositories.body_signal_repository import BodySignalRepository
from app.backend.repositories.emotion_repository import EmotionRepository
from app.backend.repositories.patient_repository import PatientRepository
from app.backend.schemas.check_in import CheckInCreate
from app.backend.services.check_in_service import CheckInService

router = APIRouter(prefix="/check-ins")


def _t(request: Request):
    return request.app.state.templates


@router.get("", response_class=HTMLResponse)
async def list_check_ins(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = CheckInService(session)
    check_ins = await service.list(scope, current_user)
    emotions_by_check_in = await service.emotion_names_by_check_in(scope, check_ins)
    body_signals_by_check_in = await service.body_signal_names_by_check_in(scope, check_ins)

    patients_by_id = {}
    creatable_patients = []
    if current_user.role in (UserRole.superadmin, UserRole.admin):
        patient_ids = sorted({c.patient_id for c in check_ins})
        patients_by_id = {p.id: p for p in await PatientRepository(session).get_by_ids(scope, patient_ids)}
        if current_user.role == UserRole.superadmin:
            creatable_patients = await PatientRepository(session).list_by_clinic(scope)

    return _t(request).TemplateResponse(
        request,
        "check_ins/list.html",
        {
            "user": current_user,
            "check_ins": check_ins,
            "patients_by_id": patients_by_id,
            "emotions_by_check_in": emotions_by_check_in,
            "body_signals_by_check_in": body_signals_by_check_in,
            "creatable_patients": creatable_patients,
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def new_check_in_form(
    request: Request,
    patient_id: int = Query(None),
    current_user: User = Depends(require_roles(UserRole.paciente)),
    session: AsyncSession = Depends(get_db),
):
    patient = None
    if current_user.role == UserRole.superadmin:
        if not patient_id:
            return RedirectResponse("/check-ins", status_code=302)
        patient = await PatientRepository(session).get_by_clinic(None, patient_id)
        if not patient:
            return RedirectResponse("/check-ins", status_code=302)
        target_clinic_id = patient.clinic_id
    else:
        target_clinic_id = current_user.clinic_id

    emotions = await EmotionRepository(session).list_by_clinic(target_clinic_id)
    body_signals = await BodySignalRepository(session).list_by_clinic(target_clinic_id)
    return _t(request).TemplateResponse(
        request,
        "check_ins/create.html",
        {"user": current_user, "patient": patient, "emotions": emotions, "body_signals": body_signals, "error": None},
    )


@router.post("/new", response_class=HTMLResponse)
async def create_check_in(
    request: Request,
    intensity: int = Form(...),
    notes: str = Form(None),
    patient_id: int = Form(None),
    emotion_ids: list[int] = Form([]),
    body_signal_ids: list[int] = Form([]),
    current_user: User = Depends(require_roles(UserRole.paciente)),
    session: AsyncSession = Depends(get_db),
):
    service = CheckInService(session)
    try:
        data = CheckInCreate(
            intensity=intensity,
            notes=notes or None,
            patient_id=patient_id,
            emotion_ids=emotion_ids,
            body_signal_ids=body_signal_ids,
        )
        await service.create(current_user, data)
    except Exception as e:
        patient = None
        target_clinic_id = current_user.clinic_id
        if current_user.role == UserRole.superadmin and patient_id:
            patient = await PatientRepository(session).get_by_clinic(None, patient_id)
            target_clinic_id = patient.clinic_id if patient else current_user.clinic_id
        emotions = await EmotionRepository(session).list_by_clinic(target_clinic_id)
        body_signals = await BodySignalRepository(session).list_by_clinic(target_clinic_id)
        return _t(request).TemplateResponse(
            request,
            "check_ins/create.html",
            {
                "user": current_user,
                "patient": patient,
                "emotions": emotions,
                "body_signals": body_signals,
                "error": str(e),
            },
        )
    return RedirectResponse("/check-ins", status_code=302)


@router.get("/{check_in_id}", response_class=HTMLResponse)
async def check_in_detail(
    request: Request,
    check_in_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = CheckInService(session)
    check_in = await service.get(scope, check_in_id, current_user)
    emotions = (await service.emotion_names_by_check_in(scope, [check_in])).get(check_in.id, [])
    body_signals = (await service.body_signal_names_by_check_in(scope, [check_in])).get(check_in.id, [])

    patient = None
    if current_user.role in (UserRole.superadmin, UserRole.admin):
        patient = await PatientRepository(session).get_by_clinic(scope, check_in.patient_id)

    return _t(request).TemplateResponse(
        request,
        "check_ins/detail.html",
        {
            "user": current_user,
            "check_in": check_in,
            "patient": patient,
            "emotions": emotions,
            "body_signals": body_signals,
        },
    )
