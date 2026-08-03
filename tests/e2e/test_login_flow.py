import app.main as main_module
from app.backend.core.security import hash_password
from app.backend.models.user import User, UserRole


async def _create_login_user(clinic, email: str, password: str, force_password_change: bool = False) -> User:
    async with main_module.AsyncSessionLocal() as session:
        user = User(
            clinic_id=clinic.id,
            email=email,
            password_hash=hash_password(password),
            name="Test",
            surname="Admin",
            role=UserRole.admin,
            force_password_change=force_password_change,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def test_login_with_valid_credentials_redirects_to_dashboard(client, e2e_clinic):
    await _create_login_user(e2e_clinic, "admin@e2e.test", "testpass123")

    response = await client.post(
        "/login", data={"email": "admin@e2e.test", "password": "testpass123"}, follow_redirects=False
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard"
    assert "integra_session" in response.cookies


async def test_login_with_wrong_password_shows_error(client, e2e_clinic):
    await _create_login_user(e2e_clinic, "admin@e2e.test", "testpass123")

    response = await client.post(
        "/login", data={"email": "admin@e2e.test", "password": "wrongpassword"}, follow_redirects=False
    )

    assert response.status_code == 200
    assert "inválidos" in response.text


async def test_login_forces_password_change_when_flagged(client, e2e_clinic):
    await _create_login_user(e2e_clinic, "admin@e2e.test", "testpass123", force_password_change=True)

    response = await client.post(
        "/login", data={"email": "admin@e2e.test", "password": "testpass123"}, follow_redirects=False
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/change-password"


async def test_protected_route_without_session_redirects_to_login(client):
    response = await client.get("/dashboard", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/login"
