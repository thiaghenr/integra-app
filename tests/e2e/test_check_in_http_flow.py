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


async def test_bot_api_requires_bearer_token(client):
    response = await client.get("/api/v1/bot/appointments")

    assert response.status_code == 401
