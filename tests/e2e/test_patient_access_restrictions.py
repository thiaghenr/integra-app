import app.main as main_module
from app.backend.core.security import hash_password
from app.backend.models.family_member import FamilyMember
from app.backend.models.patient import Patient
from app.backend.models.user import User, UserRole


async def _login(client, email: str, password: str) -> None:
    response = await client.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    assert response.status_code == 302


async def test_patient_cannot_access_patients_list(client, e2e_patient_login):
    await _login(client, e2e_patient_login["email"], e2e_patient_login["password"])

    response = await client.get("/patients")

    assert response.status_code == 403


async def test_patient_cannot_access_another_patients_detail_page(client, e2e_clinic, e2e_patient_login):
    async with main_module.AsyncSessionLocal() as session:
        other_patient = Patient(clinic_id=e2e_clinic.id, name="Outro", surname="Paciente")
        session.add(other_patient)
        await session.commit()
        await session.refresh(other_patient)

    await _login(client, e2e_patient_login["email"], e2e_patient_login["password"])

    response = await client.get(f"/patients/{other_patient.id}")

    assert response.status_code == 403


async def test_patient_cannot_access_own_patient_detail_page_either(client, e2e_patient_login):
    # /patients/{id} isn't one of the pages a patient should see at all — not even their own.
    await _login(client, e2e_patient_login["email"], e2e_patient_login["password"])
    patient = e2e_patient_login["patient"]

    response = await client.get(f"/patients/{patient.id}")

    assert response.status_code == 403


async def test_patient_cannot_access_professionals_list(client, e2e_patient_login):
    await _login(client, e2e_patient_login["email"], e2e_patient_login["password"])

    response = await client.get("/professionals")

    assert response.status_code == 403


async def test_patient_dashboard_nav_only_shows_five_allowed_pages(client, e2e_patient_login):
    await _login(client, e2e_patient_login["email"], e2e_patient_login["password"])

    response = await client.get("/dashboard")

    assert response.status_code == 200
    assert 'href="/appointments"' in response.text
    assert 'href="/family-members"' in response.text
    assert 'href="/goals"' in response.text
    assert 'href="/missions"' in response.text
    assert 'href="/patients"' not in response.text
    assert 'href="/professionals"' not in response.text
    assert 'href="/check-ins"' not in response.text


async def test_patient_sees_only_own_family_members(client, e2e_clinic, e2e_patient_login):
    patient = e2e_patient_login["patient"]
    async with main_module.AsyncSessionLocal() as session:
        other_patient = Patient(clinic_id=e2e_clinic.id, name="Outro", surname="Paciente")
        session.add(other_patient)
        await session.commit()
        await session.refresh(other_patient)

        session.add(FamilyMember(clinic_id=e2e_clinic.id, patient_id=patient.id, name="Minha Mãe", relationship="Mãe"))
        session.add(
            FamilyMember(clinic_id=e2e_clinic.id, patient_id=other_patient.id, name="Pai de Outro", relationship="Pai")
        )
        await session.commit()

    await _login(client, e2e_patient_login["email"], e2e_patient_login["password"])

    response = await client.get("/family-members")

    assert response.status_code == 200
    assert "Minha Mãe" in response.text
    assert "Pai de Outro" not in response.text


async def test_admin_still_sees_full_patients_and_professionals_lists(client, e2e_clinic):
    async with main_module.AsyncSessionLocal() as session:
        admin_user = User(
            clinic_id=e2e_clinic.id,
            email="admin4@e2e-test.com",
            password_hash=hash_password("testpass123"),
            name="Admin",
            surname="User",
            role=UserRole.admin,
        )
        session.add(admin_user)
        await session.commit()

    await _login(client, "admin4@e2e-test.com", "testpass123")

    patients_response = await client.get("/patients")
    professionals_response = await client.get("/professionals")

    assert patients_response.status_code == 200
    assert professionals_response.status_code == 200
