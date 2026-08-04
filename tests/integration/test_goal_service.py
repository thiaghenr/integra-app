import pytest
from fastapi import HTTPException

from app.backend.models.goal import ProgressStatus
from app.backend.schemas.goal import GoalCreate, GoalStatusUpdate, GoalUpdate
from app.backend.services.goal_service import GoalService


async def test_professional_creates_goal_for_patient(db_session, professional_user, professional, patient):
    service = GoalService(db_session)
    data = GoalCreate(patient_id=patient.id, title="Reduzir crises de ansiedade")

    goal = await service.create(patient.clinic_id, data, professional_user)

    assert goal.patient_id == patient.id
    assert goal.professional_id == professional.id
    assert goal.status == ProgressStatus.pending


async def test_admin_without_professional_profile_cannot_create(db_session, admin_user, patient):
    service = GoalService(db_session)
    data = GoalCreate(patient_id=patient.id, title="Reduzir crises de ansiedade")

    with pytest.raises(HTTPException) as exc_info:
        await service.create(patient.clinic_id, data, admin_user)

    assert exc_info.value.status_code == 400


async def test_patient_cannot_create_goal(db_session, patient_user, patient):
    service = GoalService(db_session)
    data = GoalCreate(patient_id=patient.id, title="Reduzir crises de ansiedade")

    with pytest.raises(HTTPException) as exc_info:
        await service.create(patient.clinic_id, data, patient_user)

    assert exc_info.value.status_code == 400


async def test_patient_can_mark_own_goal_status(db_session, professional_user, professional, patient_user, patient):
    service = GoalService(db_session)
    goal = await service.create(patient.clinic_id, GoalCreate(patient_id=patient.id, title="Meta"), professional_user)

    updated = await service.update_status(
        patient.clinic_id, goal.id, GoalStatusUpdate(status=ProgressStatus.in_progress), patient_user
    )

    assert updated.status == ProgressStatus.in_progress


async def test_patient_cannot_mark_another_patients_goal(
    db_session, professional_user, professional, patient_user, patient, other_patient
):
    service = GoalService(db_session)
    other_goal = await service.create(
        patient.clinic_id, GoalCreate(patient_id=other_patient.id, title="Meta de outro paciente"), professional_user
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.update_status(
            patient.clinic_id, other_goal.id, GoalStatusUpdate(status=ProgressStatus.completed), patient_user
        )

    assert exc_info.value.status_code == 403


async def test_patient_cannot_edit_goal_fields(db_session, professional_user, professional, patient_user, patient):
    service = GoalService(db_session)
    goal = await service.create(patient.clinic_id, GoalCreate(patient_id=patient.id, title="Meta"), professional_user)

    with pytest.raises(HTTPException) as exc_info:
        await service.update(patient.clinic_id, goal.id, GoalUpdate(title="Nova meta"), patient_user)

    assert exc_info.value.status_code == 403


async def test_professional_only_lists_own_created_goals(
    db_session, professional_user, professional, patient, other_patient, admin_user
):
    from app.backend.core.security import hash_password
    from app.backend.models.professional import Professional
    from app.backend.models.user import User, UserRole

    service = GoalService(db_session)
    await service.create(patient.clinic_id, GoalCreate(patient_id=patient.id, title="Meta 1"), professional_user)

    other_prof_user = User(
        clinic_id=patient.clinic_id,
        email="other-prof@test.com",
        password_hash=hash_password("testpass123"),
        name="Other",
        surname="Prof",
        role=UserRole.professional,
    )
    db_session.add(other_prof_user)
    await db_session.commit()
    await db_session.refresh(other_prof_user)

    other_prof = Professional(
        clinic_id=patient.clinic_id, user_id=other_prof_user.id, name="Other", surname="Prof", specialization="X"
    )
    db_session.add(other_prof)
    await db_session.commit()
    await db_session.refresh(other_prof)

    await service.create(patient.clinic_id, GoalCreate(patient_id=other_patient.id, title="Meta 2"), other_prof_user)

    own_goals = await service.list(patient.clinic_id, professional_user)
    assert len(own_goals) == 1
    assert own_goals[0].professional_id == professional.id

    all_goals = await service.list(patient.clinic_id, admin_user)
    assert len(all_goals) == 2
