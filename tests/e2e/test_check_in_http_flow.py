async def test_patient_can_log_in_create_and_view_own_check_in(client, e2e_patient_login):
    login_response = await client.post(
        "/login",
        data={"email": e2e_patient_login["email"], "password": e2e_patient_login["password"]},
        follow_redirects=False,
    )
    assert login_response.status_code == 302
    assert login_response.headers["location"] == "/dashboard"

    new_form_response = await client.get("/check-ins/new")
    assert new_form_response.status_code == 200
    assert "Intensidade" in new_form_response.text

    create_response = await client.post(
        "/check-ins/new",
        data={"intensity": "7", "notes": "Me sentindo bem hoje"},
        follow_redirects=False,
    )
    assert create_response.status_code == 302
    assert create_response.headers["location"] == "/check-ins"

    list_response = await client.get("/check-ins")
    assert list_response.status_code == 200
    assert "Me sentindo bem hoje" in list_response.text
    assert "7/10" in list_response.text


async def test_check_in_creation_requires_authentication(client):
    response = await client.post("/check-ins/new", data={"intensity": "5"}, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/login"


async def test_professional_sees_check_ins_of_own_patients_only(client, e2e_clinic):
    from datetime import datetime

    import app.main as main_module
    from app.backend.core.security import hash_password
    from app.backend.models.appointment import Appointment
    from app.backend.models.check_in import CheckIn
    from app.backend.models.patient import Patient
    from app.backend.models.professional import Professional
    from app.backend.models.user import User, UserRole

    async with main_module.AsyncSessionLocal() as session:
        admin_user = User(
            clinic_id=e2e_clinic.id,
            email="admin5@e2e-test.com",
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
            email="prof3@e2e-test.com",
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

        own_patient = Patient(clinic_id=e2e_clinic.id, name="Meu", surname="Paciente")
        other_patient = Patient(clinic_id=e2e_clinic.id, name="Outro", surname="Paciente")
        session.add_all([own_patient, other_patient])
        await session.commit()
        await session.refresh(own_patient)
        await session.refresh(other_patient)

        session.add(
            Appointment(
                clinic_id=e2e_clinic.id,
                patient_id=own_patient.id,
                professional_id=professional.id,
                scheduled_at=datetime(2026, 8, 10, 14, 0),
                created_by=admin_user.id,
            )
        )
        session.add(CheckIn(clinic_id=e2e_clinic.id, patient_id=own_patient.id, intensity=8, notes="Do meu paciente"))
        session.add(CheckIn(clinic_id=e2e_clinic.id, patient_id=other_patient.id, intensity=1, notes="Não é meu"))
        await session.commit()

    login_response = await client.post(
        "/login", data={"email": "prof3@e2e-test.com", "password": "testpass123"}, follow_redirects=False
    )
    assert login_response.status_code == 302

    response = await client.get("/check-ins")

    assert response.status_code == 200
    assert "Do meu paciente" in response.text
    assert "Não é meu" not in response.text
    assert "Meu Paciente" in response.text


async def test_bot_api_requires_bearer_token(client):
    response = await client.get("/api/v1/bot/appointments")

    assert response.status_code == 401
