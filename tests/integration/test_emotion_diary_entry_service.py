from datetime import datetime

import pytest
from fastapi import HTTPException

from app.backend.models.appointment import Appointment
from app.backend.models.user import UserRole
from app.backend.schemas.emotion_diary_entry import EmotionDiaryEntryCreate
from app.backend.services.emotion_diary_entry_service import EmotionDiaryEntryService

_ABC_FIELDS = {
    "situation": "Discussão no trabalho",
    "feeling": "Raiva",
    "perception": "Senti que fui desrespeitado",
    "thought": "Achei que ninguém me ouve",
    "behavior": "Levantei a voz",
    "reaction": "Saí da sala",
    "outcome": "Piorou um pouco",
}


def _create_data(**overrides) -> EmotionDiaryEntryCreate:
    fields = {**_ABC_FIELDS, "emotion_anger": True, **overrides}
    return EmotionDiaryEntryCreate(**fields)


async def test_patient_creates_own_entry(db_session, patient_user, patient):
    service = EmotionDiaryEntryService(db_session)

    entry = await service.create(patient_user, _create_data())

    assert entry.patient_id == patient.id
    assert entry.clinic_id == patient.clinic_id
    assert entry.emotion_anger is True
    assert entry.situation == _ABC_FIELDS["situation"]


async def test_superadmin_creates_entry_for_patient(db_session, superadmin_user, patient):
    service = EmotionDiaryEntryService(db_session)

    entry = await service.create(superadmin_user, _create_data(patient_id=patient.id))

    assert entry.patient_id == patient.id
    assert entry.clinic_id == patient.clinic_id


async def test_superadmin_without_patient_id_is_rejected(db_session, superadmin_user):
    service = EmotionDiaryEntryService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.create(superadmin_user, _create_data())

    assert exc_info.value.status_code == 400


@pytest.mark.parametrize("role", [UserRole.admin, UserRole.receptionist, UserRole.professional, UserRole.viewer])
async def test_other_roles_cannot_create_entry(db_session, clinic, patient, role):
    from tests.integration.conftest import _make_user

    user = await _make_user(db_session, clinic, role, f"{role.value}@blocked.test")
    service = EmotionDiaryEntryService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.create(user, _create_data(patient_id=patient.id))

    assert exc_info.value.status_code == 403


async def test_admin_lists_all_entries_in_clinic(db_session, admin_user, patient_user, patient, other_patient):
    service = EmotionDiaryEntryService(db_session)
    await service.create(patient_user, _create_data())
    await service.create(patient_user, _create_data(emotion_anger=False, emotion_joy=True))

    entries = await service.list(patient.clinic_id, admin_user)

    assert len(entries) == 2


async def test_patient_lists_only_own_entries(db_session, patient_user, patient, other_patient, superadmin_user):
    service = EmotionDiaryEntryService(db_session)
    await service.create(patient_user, _create_data())
    await service.create(superadmin_user, _create_data(patient_id=other_patient.id))

    entries = await service.list(patient.clinic_id, patient_user)

    assert len(entries) == 1
    assert entries[0].patient_id == patient.id


async def test_patient_cannot_view_another_patients_entry(
    db_session, patient_user, patient, other_patient, superadmin_user
):
    service = EmotionDiaryEntryService(db_session)
    other_entry = await service.create(superadmin_user, _create_data(patient_id=other_patient.id))

    with pytest.raises(HTTPException) as exc_info:
        await service.get(patient.clinic_id, other_entry.id, patient_user)

    assert exc_info.value.status_code == 403


async def test_patient_without_linked_patient_record_gets_404(db_session, clinic):
    from tests.integration.conftest import _make_user

    lone_user = await _make_user(db_session, clinic, UserRole.paciente, "lonely@test.com")
    service = EmotionDiaryEntryService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.create(lone_user, _create_data())

    assert exc_info.value.status_code == 404


async def test_list_own_paginated_returns_page_size_and_total(db_session, patient_user, patient):
    service = EmotionDiaryEntryService(db_session)
    for _ in range(7):
        await service.create(patient_user, _create_data())

    entries, total = await service.list_own_paginated(patient.clinic_id, patient_user, page=1, page_size=5)

    assert total == 7
    assert len(entries) == 5


async def test_list_own_paginated_second_page_has_remainder(db_session, patient_user, patient):
    service = EmotionDiaryEntryService(db_session)
    for _ in range(7):
        await service.create(patient_user, _create_data())

    entries, total = await service.list_own_paginated(patient.clinic_id, patient_user, page=2, page_size=5)

    assert total == 7
    assert len(entries) == 2


async def test_professional_lists_entries_only_for_own_patients(
    db_session,
    clinic,
    professional,
    professional_user,
    patient,
    other_patient,
    patient_user,
    superadmin_user,
    admin_user,
):
    db_session.add(
        Appointment(
            clinic_id=clinic.id,
            patient_id=patient.id,
            professional_id=professional.id,
            scheduled_at=datetime(2026, 8, 10, 14, 0),
            created_by=admin_user.id,
        )
    )
    await db_session.commit()

    service = EmotionDiaryEntryService(db_session)
    await service.create(patient_user, _create_data())
    await service.create(superadmin_user, _create_data(patient_id=other_patient.id))

    entries = await service.list(clinic.id, professional_user)

    assert [e.patient_id for e in entries] == [patient.id]


async def test_professional_get_own_patients_entry_succeeds(
    db_session, clinic, professional, professional_user, patient, patient_user, admin_user
):
    db_session.add(
        Appointment(
            clinic_id=clinic.id,
            patient_id=patient.id,
            professional_id=professional.id,
            scheduled_at=datetime(2026, 8, 10, 14, 0),
            created_by=admin_user.id,
        )
    )
    await db_session.commit()

    service = EmotionDiaryEntryService(db_session)
    entry = await service.create(patient_user, _create_data())

    fetched = await service.get(clinic.id, entry.id, professional_user)

    assert fetched.id == entry.id


async def test_professional_cannot_get_another_patients_entry(
    db_session, clinic, professional, professional_user, other_patient, superadmin_user
):
    service = EmotionDiaryEntryService(db_session)
    other_entry = await service.create(superadmin_user, _create_data(patient_id=other_patient.id))

    with pytest.raises(HTTPException) as exc_info:
        await service.get(clinic.id, other_entry.id, professional_user)

    assert exc_info.value.status_code == 403


async def test_professional_without_linked_professional_record_gets_404(db_session, clinic):
    from tests.integration.conftest import _make_user

    lone_user = await _make_user(db_session, clinic, UserRole.professional, "lonely-prof@test.com")
    service = EmotionDiaryEntryService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.list(clinic.id, lone_user)

    assert exc_info.value.status_code == 404


async def test_professional_with_no_patients_returns_empty_list(db_session, clinic, professional, professional_user):
    service = EmotionDiaryEntryService(db_session)

    entries = await service.list(clinic.id, professional_user)

    assert entries == []
