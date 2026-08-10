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


async def test_admin_resets_forgotten_password_and_user_can_log_in_with_it(client, e2e_clinic):
    await _create_user(e2e_clinic, "admin@e2e-test.com", "adminpass1", UserRole.admin)
    target = await _create_user(e2e_clinic, "forgot@e2e-test.com", "oldpassword1", UserRole.viewer)

    login_response = await client.post(
        "/login", data={"email": "admin@e2e-test.com", "password": "adminpass1"}, follow_redirects=False
    )
    assert login_response.status_code == 302

    edit_response = await client.post(
        f"/users/{target.id}/edit",
        data={
            "name": target.name,
            "surname": target.surname,
            "email": target.email,
            "role": target.role.value,
            "is_active": "on",
            "new_password": "brandnewpass1",
        },
        follow_redirects=False,
    )
    assert edit_response.status_code == 302, edit_response.text

    await client.get("/logout")

    old_password_login = await client.post(
        "/login", data={"email": "forgot@e2e-test.com", "password": "oldpassword1"}, follow_redirects=False
    )
    assert old_password_login.status_code == 200
    assert "inválidos" in old_password_login.text

    new_password_login = await client.post(
        "/login", data={"email": "forgot@e2e-test.com", "password": "brandnewpass1"}, follow_redirects=False
    )
    assert new_password_login.status_code == 302
    assert new_password_login.headers["location"] == "/change-password"


async def test_editing_user_without_new_password_leaves_password_unchanged(client, e2e_clinic):
    await _create_user(e2e_clinic, "admin@e2e-test.com", "adminpass1", UserRole.admin)
    target = await _create_user(e2e_clinic, "keep@e2e-test.com", "keepthispass1", UserRole.viewer)

    await client.post("/login", data={"email": "admin@e2e-test.com", "password": "adminpass1"}, follow_redirects=False)

    edit_response = await client.post(
        f"/users/{target.id}/edit",
        data={
            "name": target.name,
            "surname": target.surname,
            "email": target.email,
            "role": target.role.value,
            "is_active": "on",
        },
        follow_redirects=False,
    )
    assert edit_response.status_code == 302, edit_response.text

    await client.get("/logout")

    login_response = await client.post(
        "/login", data={"email": "keep@e2e-test.com", "password": "keepthispass1"}, follow_redirects=False
    )
    assert login_response.status_code == 302
    assert login_response.headers["location"] == "/dashboard"
