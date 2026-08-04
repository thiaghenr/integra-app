from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import clinic_scope, get_db, require_roles
from app.backend.models.goal import ProgressStatus
from app.backend.models.user import User, UserRole
from app.backend.repositories.patient_repository import PatientRepository
from app.backend.repositories.professional_repository import ProfessionalRepository
from app.backend.schemas.goal import GoalCreate, GoalStatusUpdate, GoalUpdate
from app.backend.services.goal_service import GoalService

router = APIRouter(prefix="/goals")


def _t(request: Request):
    return request.app.state.templates


@router.get("", response_class=HTMLResponse)
async def list_goals(
    request: Request,
    patient_id: int = Query(None),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.professional, UserRole.paciente)),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = GoalService(session)
    goals = await service.list(scope, current_user, patient_id=patient_id)

    patient_map = {p.id: p for p in await PatientRepository(session).list_by_clinic(scope)}
    prof_map = {p.id: p for p in await ProfessionalRepository(session).list_by_clinic(scope)}

    return _t(request).TemplateResponse(
        request,
        "goals/list.html",
        {"user": current_user, "goals": goals, "patient_map": patient_map, "prof_map": prof_map},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_goal_form(
    request: Request,
    patient_id: int = Query(None),
    current_user: User = Depends(require_roles(UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    patients = await PatientRepository(session).list_by_clinic(clinic_scope(current_user))
    return _t(request).TemplateResponse(
        request,
        "goals/create.html",
        {"user": current_user, "patients": patients, "selected_patient_id": patient_id, "error": None},
    )


@router.post("/new", response_class=HTMLResponse)
async def create_goal(
    request: Request,
    patient_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(None),
    start_date: str = Form(None),
    end_date: str = Form(None),
    current_user: User = Depends(require_roles(UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    service = GoalService(session)
    try:
        data = GoalCreate(
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
            "goals/create.html",
            {"user": current_user, "patients": patients, "selected_patient_id": patient_id, "error": str(e)},
        )
    return RedirectResponse(f"/patients/{patient_id}", status_code=302)


@router.get("/{goal_id}", response_class=HTMLResponse)
async def goal_detail(
    request: Request,
    goal_id: int,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.professional, UserRole.paciente)),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = GoalService(session)
    goal = await service.get(scope, goal_id, current_user)
    patient = await PatientRepository(session).get_by_clinic(scope, goal.patient_id)
    professional = await ProfessionalRepository(session).get(goal.professional_id)
    return _t(request).TemplateResponse(
        request,
        "goals/detail.html",
        {
            "user": current_user,
            "goal": goal,
            "patient": patient,
            "professional": professional,
            "statuses": ProgressStatus,
        },
    )


@router.get("/{goal_id}/edit", response_class=HTMLResponse)
async def edit_goal_form(
    request: Request,
    goal_id: int,
    current_user: User = Depends(require_roles(UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    service = GoalService(session)
    goal = await service.get(clinic_scope(current_user), goal_id, current_user)
    return _t(request).TemplateResponse(
        request, "goals/edit.html", {"user": current_user, "goal": goal, "statuses": ProgressStatus, "error": None}
    )


@router.post("/{goal_id}/edit", response_class=HTMLResponse)
async def update_goal(
    request: Request,
    goal_id: int,
    title: str = Form(...),
    description: str = Form(None),
    start_date: str = Form(None),
    end_date: str = Form(None),
    status: str = Form(...),
    current_user: User = Depends(require_roles(UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = GoalService(session)
    try:
        data = GoalUpdate(
            title=title,
            description=description or None,
            start_date=start_date or None,
            end_date=end_date or None,
            status=ProgressStatus(status),
        )
        await service.update(scope, goal_id, data, current_user)
    except Exception as e:
        goal = await service.get(scope, goal_id, current_user)
        return _t(request).TemplateResponse(
            request,
            "goals/edit.html",
            {"user": current_user, "goal": goal, "statuses": ProgressStatus, "error": str(e)},
        )
    return RedirectResponse(f"/goals/{goal_id}", status_code=302)


@router.post("/{goal_id}/status")
async def update_goal_status(
    goal_id: int,
    status: str = Form(...),
    current_user: User = Depends(require_roles(UserRole.professional, UserRole.paciente)),
    session: AsyncSession = Depends(get_db),
):
    service = GoalService(session)
    goal = await service.update_status(
        clinic_scope(current_user), goal_id, GoalStatusUpdate(status=ProgressStatus(status)), current_user
    )
    return RedirectResponse(f"/goals/{goal.id}", status_code=302)


@router.post("/{goal_id}/delete")
async def delete_goal(
    goal_id: int,
    current_user: User = Depends(require_roles(UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    service = GoalService(session)
    goal = await service.get(clinic_scope(current_user), goal_id, current_user)
    patient_id = goal.patient_id
    await service.soft_delete(clinic_scope(current_user), goal_id, current_user)
    return RedirectResponse(f"/patients/{patient_id}", status_code=302)
