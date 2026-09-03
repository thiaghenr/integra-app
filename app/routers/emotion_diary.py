from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import clinic_scope, get_current_user, get_db, require_roles
from app.backend.models.user import User, UserRole
from app.backend.repositories.patient_repository import PatientRepository
from app.backend.schemas.emotion_diary_entry import EmotionDiaryEntryCreate
from app.backend.services.emotion_diary_entry_service import EmotionDiaryEntryService

router = APIRouter(prefix="/emotion-diary")


def _t(request: Request):
    return request.app.state.templates


@router.get("", response_class=HTMLResponse)
async def list_entries(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = EmotionDiaryEntryService(session)
    entries = await service.list(scope, current_user)
    emotions_by_entry = service.emotion_labels_by_entry(entries)

    patients_by_id = {}
    creatable_patients = []
    if current_user.role in (UserRole.superadmin, UserRole.admin, UserRole.professional):
        patient_ids = sorted({e.patient_id for e in entries})
        patients_by_id = {p.id: p for p in await PatientRepository(session).get_by_ids(scope, patient_ids)}
        if current_user.role == UserRole.superadmin:
            creatable_patients = await PatientRepository(session).list_by_clinic(scope)

    return _t(request).TemplateResponse(
        request,
        "emotion_diary/list.html",
        {
            "user": current_user,
            "entries": entries,
            "patients_by_id": patients_by_id,
            "emotions_by_entry": emotions_by_entry,
            "creatable_patients": creatable_patients,
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def new_entry_form(
    request: Request,
    patient_id: int = Query(None),
    current_user: User = Depends(require_roles(UserRole.paciente)),
    session: AsyncSession = Depends(get_db),
):
    patient = None
    if current_user.role == UserRole.superadmin:
        if not patient_id:
            return RedirectResponse("/emotion-diary", status_code=302)
        patient = await PatientRepository(session).get_by_clinic(None, patient_id)
        if not patient:
            return RedirectResponse("/emotion-diary", status_code=302)

    return _t(request).TemplateResponse(
        request,
        "emotion_diary/create.html",
        {"user": current_user, "patient": patient, "error": None},
    )


@router.post("/new", response_class=HTMLResponse)
async def create_entry(
    request: Request,
    patient_id: int = Form(None),
    emotion_joy: bool = Form(False),
    emotion_sadness: bool = Form(False),
    emotion_fear: bool = Form(False),
    emotion_anger: bool = Form(False),
    emotion_disgust: bool = Form(False),
    emotion_surprise: bool = Form(False),
    situation: str = Form(...),
    feeling: str = Form(...),
    perception: str = Form(...),
    thought: str = Form(...),
    behavior: str = Form(...),
    reaction: str = Form(...),
    outcome: str = Form(...),
    notes: str = Form(None),
    current_user: User = Depends(require_roles(UserRole.paciente)),
    session: AsyncSession = Depends(get_db),
):
    service = EmotionDiaryEntryService(session)
    try:
        data = EmotionDiaryEntryCreate(
            patient_id=patient_id,
            emotion_joy=emotion_joy,
            emotion_sadness=emotion_sadness,
            emotion_fear=emotion_fear,
            emotion_anger=emotion_anger,
            emotion_disgust=emotion_disgust,
            emotion_surprise=emotion_surprise,
            situation=situation,
            feeling=feeling,
            perception=perception,
            thought=thought,
            behavior=behavior,
            reaction=reaction,
            outcome=outcome,
            notes=notes or None,
        )
        await service.create(current_user, data)
    except Exception as e:
        patient = None
        if current_user.role == UserRole.superadmin and patient_id:
            patient = await PatientRepository(session).get_by_clinic(None, patient_id)
        return _t(request).TemplateResponse(
            request,
            "emotion_diary/create.html",
            {"user": current_user, "patient": patient, "error": str(e)},
        )
    return RedirectResponse("/emotion-diary", status_code=302)


@router.get("/{entry_id}", response_class=HTMLResponse)
async def entry_detail(
    request: Request,
    entry_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = EmotionDiaryEntryService(session)
    entry = await service.get(scope, entry_id, current_user)
    emotions = service.emotion_labels_by_entry([entry]).get(entry.id, [])

    patient = None
    if current_user.role in (UserRole.superadmin, UserRole.admin, UserRole.professional):
        patient = await PatientRepository(session).get_by_clinic(scope, entry.patient_id)

    return _t(request).TemplateResponse(
        request,
        "emotion_diary/detail.html",
        {"user": current_user, "entry": entry, "patient": patient, "emotions": emotions},
    )
