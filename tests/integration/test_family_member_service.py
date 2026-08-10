import pytest
from fastapi import HTTPException

from app.backend.models.family_member import FamilyMember
from app.backend.services.family_member_service import FamilyMemberService


@pytest.fixture
async def own_family_member(db_session, clinic, patient):
    fm = FamilyMember(clinic_id=clinic.id, patient_id=patient.id, name="Mãe", relationship="Mãe")
    db_session.add(fm)
    await db_session.commit()
    await db_session.refresh(fm)
    return fm


@pytest.fixture
async def other_family_member(db_session, clinic, other_patient):
    fm = FamilyMember(clinic_id=clinic.id, patient_id=other_patient.id, name="Pai", relationship="Pai")
    db_session.add(fm)
    await db_session.commit()
    await db_session.refresh(fm)
    return fm


async def test_admin_lists_all_family_members_in_clinic(
    db_session, admin_user, patient, own_family_member, other_family_member
):
    service = FamilyMemberService(db_session)

    family_members = await service.list(patient.clinic_id, admin_user)

    assert len(family_members) == 2


async def test_patient_lists_only_own_family_members(
    db_session, patient_user, patient, own_family_member, other_family_member
):
    service = FamilyMemberService(db_session)

    family_members = await service.list(patient.clinic_id, patient_user)

    assert [f.id for f in family_members] == [own_family_member.id]


async def test_patient_get_own_family_member_succeeds(db_session, patient_user, patient, own_family_member):
    service = FamilyMemberService(db_session)

    fm = await service.get(patient.clinic_id, own_family_member.id, patient_user)

    assert fm.id == own_family_member.id


async def test_patient_cannot_get_another_patients_family_member(
    db_session, patient_user, patient, other_family_member
):
    service = FamilyMemberService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.get(patient.clinic_id, other_family_member.id, patient_user)

    assert exc_info.value.status_code == 403


async def test_patient_without_linked_patient_record_gets_404(db_session, clinic):
    from app.backend.models.user import UserRole
    from tests.integration.conftest import _make_user

    lone_user = await _make_user(db_session, clinic, UserRole.paciente, "lonely-fam@test.com")
    service = FamilyMemberService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.list(clinic.id, lone_user)

    assert exc_info.value.status_code == 404
