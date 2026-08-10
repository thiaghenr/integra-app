from datetime import datetime

import pytest
from fastapi import HTTPException

from app.backend.models.appointment import Appointment
from app.backend.services.appointment_service import AppointmentService


@pytest.fixture
async def own_appointment(db_session, clinic, patient, professional, admin_user):
    appt = Appointment(
        clinic_id=clinic.id,
        patient_id=patient.id,
        professional_id=professional.id,
        scheduled_at=datetime(2026, 8, 10, 14, 0),
        created_by=admin_user.id,
    )
    db_session.add(appt)
    await db_session.commit()
    await db_session.refresh(appt)
    return appt


@pytest.fixture
async def other_appointment(db_session, clinic, other_patient, professional, admin_user):
    appt = Appointment(
        clinic_id=clinic.id,
        patient_id=other_patient.id,
        professional_id=professional.id,
        scheduled_at=datetime(2026, 8, 11, 15, 0),
        created_by=admin_user.id,
    )
    db_session.add(appt)
    await db_session.commit()
    await db_session.refresh(appt)
    return appt


async def test_patient_list_returns_only_own_appointments(
    db_session, patient_user, patient, own_appointment, other_appointment
):
    service = AppointmentService(db_session)

    appointments = await service.list(patient.clinic_id, patient_user)

    assert [a.id for a in appointments] == [own_appointment.id]


async def test_patient_get_own_appointment_succeeds(db_session, patient_user, patient, own_appointment):
    service = AppointmentService(db_session)

    appt = await service.get(patient.clinic_id, own_appointment.id, patient_user)

    assert appt.id == own_appointment.id


async def test_patient_cannot_get_another_patients_appointment(db_session, patient_user, patient, other_appointment):
    service = AppointmentService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.get(patient.clinic_id, other_appointment.id, patient_user)

    assert exc_info.value.status_code == 403


async def test_patient_without_linked_patient_record_gets_404_on_list(db_session, clinic):
    from app.backend.models.user import UserRole
    from tests.integration.conftest import _make_user

    lone_user = await _make_user(db_session, clinic, UserRole.paciente, "lonely-appt@test.com")
    service = AppointmentService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.list(clinic.id, lone_user)

    assert exc_info.value.status_code == 404
