import pytest
from fastapi import HTTPException

from app.backend.schemas.medical_record import MedicalRecordCreate
from app.backend.services.medical_record_service import MedicalRecordService


async def test_admin_creating_a_record_without_professional_id_raises_cleanly(db_session, admin_user, patient):
    # Regression test: admin/superadmin have no "own" Professional row, so the
    # service used to silently derive professional_id=None and let it hit the
    # DB's NOT NULL constraint as a raw IntegrityError instead of a clean 400.
    service = MedicalRecordService(db_session)
    data = MedicalRecordCreate(patient_id=patient.id, title="Avaliação", content="Notas")

    with pytest.raises(HTTPException) as exc_info:
        await service.create(admin_user.clinic_id, data, admin_user)

    assert exc_info.value.status_code == 400


async def test_admin_creating_a_record_with_professional_id_succeeds(db_session, admin_user, patient, professional):
    service = MedicalRecordService(db_session)
    data = MedicalRecordCreate(
        patient_id=patient.id, professional_id=professional.id, title="Avaliação", content="Notas"
    )

    record = await service.create(admin_user.clinic_id, data, admin_user)

    assert record.professional_id == professional.id


async def test_professional_creating_a_record_ignores_submitted_professional_id(
    db_session, professional_user, professional, patient
):
    # A professional must never be able to create a record under someone
    # else's professional_id, even if the client submits one.
    service = MedicalRecordService(db_session)
    data = MedicalRecordCreate(patient_id=patient.id, professional_id=999999, title="Avaliação", content="Notas")

    record = await service.create(professional_user.clinic_id, data, professional_user)

    assert record.professional_id == professional.id


async def test_professional_without_a_linked_professional_row_raises_cleanly(db_session, professional_user, patient):
    # professional_user has no linked Professional row in this test (the
    # `professional` fixture wasn't requested) — same failure mode as admin.
    service = MedicalRecordService(db_session)
    data = MedicalRecordCreate(patient_id=patient.id, title="Avaliação", content="Notas")

    with pytest.raises(HTTPException) as exc_info:
        await service.create(professional_user.clinic_id, data, professional_user)

    assert exc_info.value.status_code == 400
