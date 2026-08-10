from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import clinic_scope, get_current_user, get_db, require_roles
from app.backend.models.user import User, UserRole
from app.backend.repositories.patient_repository import PatientRepository
from app.backend.schemas.family_member import FamilyMemberCreate, FamilyMemberUpdate
from app.backend.services.family_member_service import FamilyMemberService

router = APIRouter(prefix="/family-members")


def _t(request: Request):
    return request.app.state.templates


@router.get("", response_class=HTMLResponse)
async def list_family_members(
    request: Request,
    patient_id: int = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = FamilyMemberService(session)
    family_members = await service.list(scope, current_user, patient_id=patient_id)

    patient_ids = sorted({f.patient_id for f in family_members})
    patients_by_id = {p.id: p for p in await PatientRepository(session).get_by_ids(scope, patient_ids)}

    return _t(request).TemplateResponse(
        request,
        "family_members/list.html",
        {"user": current_user, "family_members": family_members, "patients_by_id": patients_by_id},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_family_member_form(
    request: Request,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.receptionist)),
    session: AsyncSession = Depends(get_db),
):
    patients = await PatientRepository(session).list_by_clinic(current_user.clinic_id)
    return _t(request).TemplateResponse(
        request, "family_members/create.html", {"user": current_user, "patients": patients, "error": None}
    )


@router.post("/new", response_class=HTMLResponse)
async def create_family_member(
    request: Request,
    patient_id: int = Form(...),
    name: str = Form(...),
    relationship: str = Form(...),
    phone: str = Form(None),
    email: str = Form(None),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.receptionist)),
    session: AsyncSession = Depends(get_db),
):
    service = FamilyMemberService(session)
    target_clinic_id = current_user.clinic_id
    try:
        data = FamilyMemberCreate(
            patient_id=patient_id,
            name=name,
            relationship=relationship,
            phone=phone or None,
            email=email or None,
        )
        await service.create(target_clinic_id, data)
    except Exception as e:
        patients = await PatientRepository(session).list_by_clinic(target_clinic_id)
        return _t(request).TemplateResponse(
            request,
            "family_members/create.html",
            {"user": current_user, "patients": patients, "error": str(e)},
        )
    return RedirectResponse("/family-members", status_code=302)


@router.get("/{family_member_id}/edit", response_class=HTMLResponse)
async def edit_family_member_form(
    request: Request,
    family_member_id: int,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.receptionist)),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = FamilyMemberService(session)
    family_member = await service.get(scope, family_member_id, current_user)
    patient = await PatientRepository(session).get_by_clinic(scope, family_member.patient_id)
    return _t(request).TemplateResponse(
        request,
        "family_members/edit.html",
        {"user": current_user, "family_member": family_member, "patient": patient, "error": None},
    )


@router.post("/{family_member_id}/edit", response_class=HTMLResponse)
async def update_family_member(
    request: Request,
    family_member_id: int,
    name: str = Form(...),
    relationship: str = Form(...),
    phone: str = Form(None),
    email: str = Form(None),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.receptionist)),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = FamilyMemberService(session)
    try:
        data = FamilyMemberUpdate(
            name=name,
            relationship=relationship,
            phone=phone or None,
            email=email or None,
        )
        await service.update(scope, family_member_id, data, current_user)
    except Exception as e:
        family_member = await service.get(scope, family_member_id, current_user)
        patient = await PatientRepository(session).get_by_clinic(scope, family_member.patient_id)
        return _t(request).TemplateResponse(
            request,
            "family_members/edit.html",
            {"user": current_user, "family_member": family_member, "patient": patient, "error": str(e)},
        )
    return RedirectResponse("/family-members", status_code=302)


@router.post("/{family_member_id}/delete")
async def delete_family_member(
    family_member_id: int,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.receptionist)),
    session: AsyncSession = Depends(get_db),
):
    service = FamilyMemberService(session)
    await service.soft_delete(clinic_scope(current_user), family_member_id, current_user)
    return RedirectResponse("/family-members", status_code=302)
