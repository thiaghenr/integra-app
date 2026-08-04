from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import clinic_scope, get_db, require_roles
from app.backend.models.goal import ProgressStatus
from app.backend.models.user import User, UserRole
from app.backend.repositories.patient_repository import PatientRepository
from app.backend.repositories.professional_repository import ProfessionalRepository
from app.backend.schemas.mission import MissionCreate, MissionStatusUpdate, MissionUpdate
from app.backend.services.mission_service import MissionService

router = APIRouter(prefix="/missions")


def _t(request: Request):
    return request.app.state.templates


@router.get("", response_class=HTMLResponse)
async def list_missions(
    request: Request,
    patient_id: int = Query(None),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.professional, UserRole.paciente)),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = MissionService(session)
    missions = await service.list(scope, current_user, patient_id=patient_id)

    patient_map = {p.id: p for p in await PatientRepository(session).list_by_clinic(scope)}
    prof_map = {p.id: p for p in await ProfessionalRepository(session).list_by_clinic(scope)}

    return _t(request).TemplateResponse(
        request,
        "missions/list.html",
        {"user": current_user, "missions": missions, "patient_map": patient_map, "prof_map": prof_map},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_mission_form(
    request: Request,
    patient_id: int = Query(None),
    current_user: User = Depends(require_roles(UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    patients = await PatientRepository(session).list_by_clinic(clinic_scope(current_user))
    return _t(request).TemplateResponse(
        request,
        "missions/create.html",
        {"user": current_user, "patients": patients, "selected_patient_id": patient_id, "error": None},
    )


@router.post("/new", response_class=HTMLResponse)
async def create_mission(
    request: Request,
    patient_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(None),
    start_date: str = Form(None),
    end_date: str = Form(None),
    current_user: User = Depends(require_roles(UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    service = MissionService(session)
    try:
        data = MissionCreate(
            patient_id=patient_id,
            title=title,
            description=description or None,
            start_date=start_date or None,
            end_date=end_date or None,
        )
        await service.create(current_user.clinic_id, data, current_user)
    except Exception as e:
        patients = await PatientRepository(session).list_by_clinic(clinic_scope(current_user))
        return _t(request).TemplateResponse(
            request,
            "missions/create.html",
            {"user": current_user, "patients": patients, "selected_patient_id": patient_id, "error": str(e)},
        )
    return RedirectResponse(f"/patients/{patient_id}", status_code=302)


@router.get("/{mission_id}", response_class=HTMLResponse)
async def mission_detail(
    request: Request,
    mission_id: int,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.professional, UserRole.paciente)),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = MissionService(session)
    mission = await service.get(scope, mission_id, current_user)
    patient = await PatientRepository(session).get_by_clinic(scope, mission.patient_id)
    professional = await ProfessionalRepository(session).get(mission.professional_id)
    return _t(request).TemplateResponse(
        request,
        "missions/detail.html",
        {
            "user": current_user,
            "mission": mission,
            "patient": patient,
            "professional": professional,
            "statuses": ProgressStatus,
        },
    )


@router.get("/{mission_id}/edit", response_class=HTMLResponse)
async def edit_mission_form(
    request: Request,
    mission_id: int,
    current_user: User = Depends(require_roles(UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    service = MissionService(session)
    mission = await service.get(clinic_scope(current_user), mission_id, current_user)
    return _t(request).TemplateResponse(
        request,
        "missions/edit.html",
        {"user": current_user, "mission": mission, "statuses": ProgressStatus, "error": None},
    )


@router.post("/{mission_id}/edit", response_class=HTMLResponse)
async def update_mission(
    request: Request,
    mission_id: int,
    title: str = Form(...),
    description: str = Form(None),
    start_date: str = Form(None),
    end_date: str = Form(None),
    status: str = Form(...),
    current_user: User = Depends(require_roles(UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = MissionService(session)
    try:
        data = MissionUpdate(
            title=title,
            description=description or None,
            start_date=start_date or None,
            end_date=end_date or None,
            status=ProgressStatus(status),
        )
        await service.update(scope, mission_id, data, current_user)
    except Exception as e:
        mission = await service.get(scope, mission_id, current_user)
        return _t(request).TemplateResponse(
            request,
            "missions/edit.html",
            {"user": current_user, "mission": mission, "statuses": ProgressStatus, "error": str(e)},
        )
    return RedirectResponse(f"/missions/{mission_id}", status_code=302)


@router.post("/{mission_id}/status")
async def update_mission_status(
    mission_id: int,
    status: str = Form(...),
    current_user: User = Depends(require_roles(UserRole.professional, UserRole.paciente)),
    session: AsyncSession = Depends(get_db),
):
    service = MissionService(session)
    mission = await service.update_status(
        clinic_scope(current_user), mission_id, MissionStatusUpdate(status=ProgressStatus(status)), current_user
    )
    return RedirectResponse(f"/missions/{mission.id}", status_code=302)


@router.post("/{mission_id}/delete")
async def delete_mission(
    mission_id: int,
    current_user: User = Depends(require_roles(UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    service = MissionService(session)
    mission = await service.get(clinic_scope(current_user), mission_id, current_user)
    patient_id = mission.patient_id
    await service.soft_delete(clinic_scope(current_user), mission_id, current_user)
    return RedirectResponse(f"/patients/{patient_id}", status_code=302)
