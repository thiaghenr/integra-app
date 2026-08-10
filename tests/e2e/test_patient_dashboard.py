from datetime import datetime

import app.main as main_module
from app.backend.core.security import hash_password
from app.backend.models.appointment import Appointment
from app.backend.models.check_in import CheckIn
from app.backend.models.goal import Goal
from app.backend.models.mission import Mission
from app.backend.models.patient import Patient
from app.backend.models.professional import Professional
from app.backend.models.user import User, UserRole


async def _login(client, email: str, password: str) -> None:
    response = await client.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard"


async def test_patient_dashboard_shows_own_check_ins_goals_missions_and_schedule(client, e2e_clinic, e2e_patient_login):
    async with main_module.AsyncSessionLocal() as session:
        admin_user = User(
            clinic_id=e2e_clinic.id,
            email="admin3@e2e-test.com",
            password_hash=hash_password("testpass123"),
            name="Admin",
            surname="User",
            role=UserRole.admin,
        )
        session.add(admin_user)
        await session.commit()
        await session.refresh(admin_user)

        prof_user = User(
            clinic_id=e2e_clinic.id,
            email="prof2@e2e-test.com",
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

        other_patient = Patient(clinic_id=e2e_clinic.id, name="Outro", surname="Paciente")
        session.add(other_patient)
        await session.commit()
        await session.refresh(other_patient)

        patient = e2e_patient_login["patient"]

        session.add(CheckIn(clinic_id=e2e_clinic.id, patient_id=patient.id, intensity=6, notes="Meu check-in"))
        session.add(CheckIn(clinic_id=e2e_clinic.id, patient_id=other_patient.id, intensity=1, notes="Não é meu"))
        session.add(
            Goal(clinic_id=e2e_clinic.id, patient_id=patient.id, professional_id=professional.id, title="Minha Meta")
        )
        session.add(
            Mission(
                clinic_id=e2e_clinic.id,
                patient_id=patient.id,
                professional_id=professional.id,
                title="Minha Missão",
            )
        )
        session.add(
            Appointment(
                clinic_id=e2e_clinic.id,
                patient_id=patient.id,
                professional_id=professional.id,
                scheduled_at=datetime(2026, 8, 10, 14, 0),
                created_by=admin_user.id,
            )
        )
        await session.commit()

    await _login(client, e2e_patient_login["email"], e2e_patient_login["password"])

    response = await client.get("/dashboard")

    assert response.status_code == 200
    assert "Meu check-in" in response.text
    assert "Não é meu" not in response.text
    assert "Minha Meta" in response.text
    assert "Minha Missão" in response.text
    assert "Joana Silva" in response.text


async def test_patient_dashboard_check_ins_paginate_five_per_page(client, e2e_patient_login):
    patient = e2e_patient_login["patient"]
    async with main_module.AsyncSessionLocal() as session:
        for i in range(7):
            session.add(
                CheckIn(
                    clinic_id=patient.clinic_id, patient_id=patient.id, intensity=(i % 10) + 1, notes=f"Check-in {i}"
                )
            )
        await session.commit()

    await _login(client, e2e_patient_login["email"], e2e_patient_login["password"])

    page_one = await client.get("/dashboard")
    assert page_one.status_code == 200
    assert "Página 1 de 2" in page_one.text
    assert page_one.text.count('btn-secondary btn-sm">Ver</a>') == 5

    page_two = await client.get("/dashboard?page=2")
    assert page_two.status_code == 200
    assert "Página 2 de 2" in page_two.text
    assert page_two.text.count('btn-secondary btn-sm">Ver</a>') == 2
