import app.main as main_module
from app.backend.core.security import hash_password
from app.backend.models.user import User, UserRole


async def _create_user(clinic, email: str, password: str, role: UserRole) -> User:
    async with main_module.AsyncSessionLocal() as session:
        user = User(
            clinic_id=clinic.id,
            email=email,
            password_hash=hash_password(password),
            name="Test",
            surname=role.value.capitalize(),
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _login_admin(client, clinic):
    await _create_user(clinic, "admin@e2e-test.com", "adminpass1", UserRole.admin)
    response = await client.post(
        "/login", data={"email": "admin@e2e-test.com", "password": "adminpass1"}, follow_redirects=False
    )
    assert response.status_code == 302


async def test_new_user_form_does_not_offer_paciente_or_professional(client, e2e_clinic):
    await _login_admin(client, e2e_clinic)

    response = await client.get("/users/new")

    assert response.status_code == 200
    assert 'value="paciente"' not in response.text
    assert 'value="professional"' not in response.text
    assert 'value="admin"' in response.text


async def test_create_user_rejects_paciente_role(client, e2e_clinic):
    await _login_admin(client, e2e_clinic)

    response = await client.post(
        "/users/new",
        data={
            "name": "Orphan",
            "surname": "Paciente",
            "email": "orphan@e2e-test.com",
            "password": "somepassword1",
            "role": "paciente",
        },
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert "Pacientes/Profissionais" in response.text


async def test_create_user_rejects_professional_role(client, e2e_clinic):
    await _login_admin(client, e2e_clinic)

    response = await client.post(
        "/users/new",
        data={
            "name": "Orphan",
            "surname": "Prof",
            "email": "orphanprof@e2e-test.com",
            "password": "somepassword1",
            "role": "professional",
        },
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert "Pacientes/Profissionais" in response.text


async def test_create_user_still_allows_receptionist_role(client, e2e_clinic):
    await _login_admin(client, e2e_clinic)

    response = await client.post(
        "/users/new",
        data={
            "name": "Front",
            "surname": "Desk",
            "email": "frontdesk@e2e-test.com",
            "password": "somepassword1",
            "role": "receptionist",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/users"


async def test_edit_user_rejects_promoting_existing_user_to_paciente(client, e2e_clinic):
    await _login_admin(client, e2e_clinic)
    target = await _create_user(e2e_clinic, "viewer@e2e-test.com", "viewerpass1", UserRole.viewer)

    response = await client.post(
        f"/users/{target.id}/edit",
        data={
            "name": target.name,
            "surname": target.surname,
            "email": target.email,
            "role": "paciente",
            "is_active": "on",
        },
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert "Pacientes/Profissionais" in response.text


async def test_edit_user_allows_keeping_existing_paciente_role_unchanged(client, e2e_clinic):
    await _login_admin(client, e2e_clinic)
    target = await _create_user(e2e_clinic, "patient@e2e-test.com", "patientpass1", UserRole.paciente)

    response = await client.post(
        f"/users/{target.id}/edit",
        data={
            "name": target.name,
            "surname": target.surname,
            "email": target.email,
            "role": "paciente",
            "is_active": "on",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/users"
