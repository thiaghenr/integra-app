import pytest


@pytest.fixture
def mock_import(monkeypatch):
    async def _fake_import_material_html(url: str) -> tuple[str, str]:
        return "fake-doc-id-123", "<p>Respire fundo por 5 segundos.</p>"

    monkeypatch.setattr(
        "app.backend.services.material_service.import_material_html",
        _fake_import_material_html,
    )
    return _fake_import_material_html


async def test_patient_cannot_access_import_form(client, e2e_patient_login):
    login_response = await client.post(
        "/login",
        data={"email": e2e_patient_login["email"], "password": e2e_patient_login["password"]},
        follow_redirects=False,
    )
    assert login_response.status_code == 302

    response = await client.get("/materials/new")

    assert response.status_code == 403


async def test_patient_cannot_submit_import(client, e2e_patient_login, mock_import):
    await client.post(
        "/login",
        data={"email": e2e_patient_login["email"], "password": e2e_patient_login["password"]},
        follow_redirects=False,
    )

    response = await client.post(
        "/materials/new",
        data={"title": "Tentando importar", "level": "1", "source_url": "https://docs.google.com/document/d/abc/edit"},
    )

    assert response.status_code == 403


async def test_materials_require_authentication(client):
    response = await client.get("/materials", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/login"


async def test_admin_imports_material_and_patient_sees_it_when_level_allows(client, e2e_clinic, mock_import):
    import app.main as main_module
    from app.backend.core.security import hash_password
    from app.backend.models.patient import Patient
    from app.backend.models.user import User, UserRole

    async with main_module.AsyncSessionLocal() as session:
        admin_user = User(
            clinic_id=e2e_clinic.id,
            email="admin-materials@e2e.test",
            password_hash=hash_password("testpass123"),
            name="Admin",
            surname="User",
            role=UserRole.admin,
        )
        session.add(admin_user)

        patient_user = User(
            clinic_id=e2e_clinic.id,
            email="patient-materials@e2e.test",
            password_hash=hash_password("testpass123"),
            name="Paciente",
            surname="Nivel Dois",
            role=UserRole.paciente,
        )
        session.add(patient_user)
        await session.commit()
        await session.refresh(admin_user)
        await session.refresh(patient_user)

        patient = Patient(
            clinic_id=e2e_clinic.id, user_id=patient_user.id, name="Paciente", surname="Nivel Dois", level=2
        )
        session.add(patient)
        await session.commit()

    admin_login = await client.post(
        "/login", data={"email": "admin-materials@e2e.test", "password": "testpass123"}, follow_redirects=False
    )
    assert admin_login.status_code == 302

    create_response = await client.post(
        "/materials/new",
        data={
            "title": "Respiração diafragmática",
            "level": "2",
            "source_url": "https://docs.google.com/document/d/abc/edit",
        },
        follow_redirects=False,
    )
    assert create_response.status_code == 302
    material_url = create_response.headers["location"]

    await client.get("/logout", follow_redirects=False)

    patient_login = await client.post(
        "/login", data={"email": "patient-materials@e2e.test", "password": "testpass123"}, follow_redirects=False
    )
    assert patient_login.status_code == 302

    list_response = await client.get("/materials")
    assert list_response.status_code == 200
    assert "Respiração diafragmática" in list_response.text

    detail_response = await client.get(material_url)
    assert detail_response.status_code == 200
    assert "Respire fundo por 5 segundos." in detail_response.text


async def test_patient_below_required_level_cannot_view_material_by_url(client, e2e_clinic, mock_import):
    import app.main as main_module
    from app.backend.core.security import hash_password
    from app.backend.models.patient import Patient
    from app.backend.models.user import User, UserRole

    async with main_module.AsyncSessionLocal() as session:
        admin_user = User(
            clinic_id=e2e_clinic.id,
            email="admin-materials2@e2e.test",
            password_hash=hash_password("testpass123"),
            name="Admin",
            surname="User",
            role=UserRole.admin,
        )
        session.add(admin_user)

        patient_user = User(
            clinic_id=e2e_clinic.id,
            email="patient-materials2@e2e.test",
            password_hash=hash_password("testpass123"),
            name="Paciente",
            surname="Nivel Um",
            role=UserRole.paciente,
        )
        session.add(patient_user)
        await session.commit()
        await session.refresh(admin_user)
        await session.refresh(patient_user)

        patient = Patient(
            clinic_id=e2e_clinic.id, user_id=patient_user.id, name="Paciente", surname="Nivel Um", level=1
        )
        session.add(patient)
        await session.commit()

    await client.post(
        "/login", data={"email": "admin-materials2@e2e.test", "password": "testpass123"}, follow_redirects=False
    )
    create_response = await client.post(
        "/materials/new",
        data={"title": "Material avançado", "level": "5", "source_url": "https://docs.google.com/document/d/abc/edit"},
        follow_redirects=False,
    )
    material_url = create_response.headers["location"]

    await client.get("/logout", follow_redirects=False)
    await client.post(
        "/login", data={"email": "patient-materials2@e2e.test", "password": "testpass123"}, follow_redirects=False
    )

    list_response = await client.get("/materials")
    assert "Material avançado" not in list_response.text

    detail_response = await client.get(material_url)
    assert detail_response.status_code == 403
