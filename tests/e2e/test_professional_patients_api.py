from datetime import datetime

import app.main as main_module
from app.backend.core.security import create_jwt, hash_password
from app.backend.models.appointment import Appointment
from app.backend.models.patient import Patient
from app.backend.models.professional import Professional
from app.backend.models.user import User, UserRole


async def test_professional_sees_only_own_patients_via_bot_free_api(client, e2e_clinic):
    async with main_module.AsyncSessionLocal() as session:
        prof_user = User(
            clinic_id=e2e_clinic.id,
            email="prof@e2e-test.com",
            password_hash=hash_password("testpass123"),
            name="Joana",
            surname="Silva",
            role=UserRole.professional,
        )
        session.add(prof_user)
        await session.commit()
        await session.refresh(prof_user)

        professional = Professional(
            clinic_id=e2e_clinic.id, user_id=prof_user.id, name="Joana", surname="Silva", specialization="Psicologia"
        )
        session.add(professional)
        await session.commit()
        await session.refresh(professional)

        seen_patient = Patient(clinic_id=e2e_clinic.id, name="Maria", surname="Souza")
        unrelated_patient = Patient(clinic_id=e2e_clinic.id, name="Outro", surname="Paciente")
        session.add_all([seen_patient, unrelated_patient])
        await session.commit()
        await session.refresh(seen_patient)
        await session.refresh(unrelated_patient)

        admin_user = User(
            clinic_id=e2e_clinic.id,
            email="admin2@e2e-test.com",
            password_hash=hash_password("testpass123"),
            name="Admin",
            surname="User",
            role=UserRole.admin,
        )
        session.add(admin_user)
        await session.commit()
        await session.refresh(admin_user)

        session.add(
            Appointment(
                clinic_id=e2e_clinic.id,
                patient_id=seen_patient.id,
                professional_id=professional.id,
                scheduled_at=datetime(2026, 8, 10, 14, 0),
                created_by=admin_user.id,
            )
        )
        await session.commit()

    token = create_jwt(prof_user.id)

    response = await client.get("/api/v1/professionals/me/patients", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert [p["id"] for p in body] == [seen_patient.id]


async def test_me_patients_returns_404_when_no_linked_professional(client, e2e_patient_login):
    token = create_jwt(e2e_patient_login["user"].id)

    response = await client.get("/api/v1/professionals/me/patients", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 404


async def test_me_patients_requires_bearer_token(client):
    response = await client.get("/api/v1/professionals/me/patients")

    assert response.status_code == 401
