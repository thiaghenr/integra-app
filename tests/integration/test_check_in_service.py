import pytest
from fastapi import HTTPException

from app.backend.models.emotion import Emotion
from app.backend.models.user import UserRole
from app.backend.schemas.check_in import CheckInCreate
from app.backend.services.check_in_service import CheckInService


@pytest.fixture
async def emotion(db_session, clinic):
    e = Emotion(clinic_id=clinic.id, name="Feliz")
    db_session.add(e)
    await db_session.commit()
    await db_session.refresh(e)
    return e


async def test_patient_creates_own_check_in(db_session, patient_user, patient):
    service = CheckInService(db_session)
    data = CheckInCreate(intensity=7, notes="Dia bom")

    check_in = await service.create(patient_user, data)

    assert check_in.patient_id == patient.id
    assert check_in.clinic_id == patient.clinic_id
    assert check_in.intensity == 7


async def test_superadmin_creates_check_in_for_patient(db_session, superadmin_user, patient):
    service = CheckInService(db_session)
    data = CheckInCreate(intensity=5, patient_id=patient.id)

    check_in = await service.create(superadmin_user, data)

    assert check_in.patient_id == patient.id
    assert check_in.clinic_id == patient.clinic_id


async def test_superadmin_without_patient_id_is_rejected(db_session, superadmin_user):
    service = CheckInService(db_session)
    data = CheckInCreate(intensity=5)

    with pytest.raises(HTTPException) as exc_info:
        await service.create(superadmin_user, data)

    assert exc_info.value.status_code == 400


@pytest.mark.parametrize("role", [UserRole.admin, UserRole.receptionist, UserRole.professional, UserRole.viewer])
async def test_other_roles_cannot_create_check_in(db_session, clinic, patient, role):
    from tests.integration.conftest import _make_user

    user = await _make_user(db_session, clinic, role, f"{role.value}@blocked.test")
    service = CheckInService(db_session)
    data = CheckInCreate(intensity=5, patient_id=patient.id)

    with pytest.raises(HTTPException) as exc_info:
        await service.create(user, data)

    assert exc_info.value.status_code == 403


async def test_invalid_emotion_id_is_rejected(db_session, patient_user, patient):
    service = CheckInService(db_session)
    data = CheckInCreate(intensity=5, emotion_ids=[999999])

    with pytest.raises(HTTPException) as exc_info:
        await service.create(patient_user, data)

    assert exc_info.value.status_code == 400


async def test_valid_emotion_is_linked(db_session, patient_user, patient, emotion):
    service = CheckInService(db_session)
    data = CheckInCreate(intensity=5, emotion_ids=[emotion.id])

    check_in = await service.create(patient_user, data)
    names = await service.emotion_names_by_check_in(patient.clinic_id, [check_in])

    assert names[check_in.id] == ["Feliz"]


async def test_admin_lists_all_check_ins_in_clinic(db_session, admin_user, patient_user, patient, other_patient):
    service = CheckInService(db_session)
    await service.create(patient_user, CheckInCreate(intensity=3))
    await service.create(patient_user, CheckInCreate(intensity=8))

    check_ins = await service.list(patient.clinic_id, admin_user)

    assert len(check_ins) == 2


async def test_patient_lists_only_own_check_ins(db_session, patient_user, patient, other_patient, superadmin_user):
    service = CheckInService(db_session)
    await service.create(patient_user, CheckInCreate(intensity=3))
    await service.create(superadmin_user, CheckInCreate(intensity=9, patient_id=other_patient.id))

    check_ins = await service.list(patient.clinic_id, patient_user)

    assert len(check_ins) == 1
    assert check_ins[0].patient_id == patient.id


async def test_patient_cannot_view_another_patients_check_in(
    db_session, patient_user, patient, other_patient, superadmin_user
):
    service = CheckInService(db_session)
    other_check_in = await service.create(superadmin_user, CheckInCreate(intensity=9, patient_id=other_patient.id))

    with pytest.raises(HTTPException) as exc_info:
        await service.get(patient.clinic_id, other_check_in.id, patient_user)

    assert exc_info.value.status_code == 403


async def test_patient_without_linked_patient_record_gets_404(db_session, clinic):
    from tests.integration.conftest import _make_user

    lone_user = await _make_user(db_session, clinic, UserRole.paciente, "lonely@test.com")
    service = CheckInService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.create(lone_user, CheckInCreate(intensity=5))

    assert exc_info.value.status_code == 404
