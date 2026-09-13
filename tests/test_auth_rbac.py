import pytest


@pytest.mark.asyncio
async def test_teacher_login_success(
    client,
    seeded_users,
):
    response = await client.post(
        "/auth/login",
        json={
            "login_id": "teacher.test",
            "password": "Teacher123!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_student_login_success(
    client,
    seeded_users,
):
    response = await client.post(
        "/auth/login",
        json={
            "login_id": "student.test",
            "password": "Student123!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(
    client,
    seeded_users,
):
    response = await client.post(
        "/auth/login",
        json={
            "login_id": "teacher.test",
            "password": "WrongPassword!",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_rejects_unknown_user(
    client,
    seeded_users,
):
    response = await client.post(
        "/auth/login",
        json={
            "login_id": "does.not.exist",
            "password": "Whatever123!",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_returns_teacher(
    client,
    seeded_users,
):
    login_response = await client.post(
        "/auth/login",
        json={
            "login_id": "teacher.test",
            "password": "Teacher123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = await client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["login_id"] == "teacher.test"
    assert data["role"] == "teacher"
    assert data["full_name"] == "Test Teacher"


@pytest.mark.asyncio
async def test_teacher_can_access_teacher_route(
    client,
    seeded_users,
):
    login_response = await client.post(
        "/auth/login",
        json={
            "login_id": "teacher.test",
            "password": "Teacher123!",
        },
    )

    token = login_response.json()["access_token"]

    response = await client.get(
        "/teacher/classes",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["name"] == "Form 2 Test"


@pytest.mark.asyncio
async def test_student_cannot_access_teacher_route(
    client,
    seeded_users,
):
    login_response = await client.post(
        "/auth/login",
        json={
            "login_id": "student.test",
            "password": "Student123!",
        },
    )

    token = login_response.json()["access_token"]

    response = await client.get(
        "/teacher/classes",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_access_teacher_route(
    client,
):
    response = await client.get(
        "/teacher/classes",
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_malformed_token_is_rejected(
    client,
):
    response = await client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401
