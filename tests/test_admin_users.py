import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.school import School
from app.models.user import User


async def login(
    client,
    login_id: str,
    password: str,
) -> dict[str, str]:
    response = await client.post(
        "/auth/login",
        json={
            "login_id": login_id,
            "password": password,
        },
    )

    assert response.status_code == 200

    return {
        "Authorization": (
            f"Bearer {response.json()['access_token']}"
        ),
    }


@pytest.mark.asyncio
async def test_admin_can_list_users_in_own_school(
    client,
    seeded_users,
):
    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.get(
        "/admin/users",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 3

    login_ids = {
        user["login_id"]
        for user in data
    }

    assert login_ids == {
        "teacher.test",
        "student.test",
        "admin.test",
    }

    for user in data:
        assert (
            user["school_id"]
            == seeded_users["school"].id
        )


@pytest.mark.asyncio
async def test_admin_user_list_excludes_other_school_users(
    client,
    db_session,
    seeded_users,
):
    other_school = School(
        name="Other Secondary School",
        code="OTHER-001",
        is_active=True,
    )

    db_session.add(other_school)
    await db_session.flush()

    foreign_teacher = User(
        school_id=other_school.id,
        login_id="foreign.teacher",
        full_name="Foreign Teacher",
        role=UserRole.TEACHER,
        password_hash=hash_password(
            "Foreign123!"
        ),
        is_active=True,
    )

    foreign_student = User(
        school_id=other_school.id,
        login_id="foreign.student",
        full_name="Foreign Student",
        role=UserRole.STUDENT,
        password_hash=hash_password(
            "Foreign123!"
        ),
        is_active=True,
    )

    db_session.add_all(
        [
            foreign_teacher,
            foreign_student,
        ]
    )

    await db_session.commit()

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.get(
        "/admin/users",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    login_ids = {
        user["login_id"]
        for user in data
    }

    assert "foreign.teacher" not in login_ids
    assert "foreign.student" not in login_ids

    assert all(
        user["school_id"]
        == seeded_users["school"].id
        for user in data
    )


@pytest.mark.asyncio
async def test_teacher_cannot_list_admin_users(
    client,
    seeded_users,
):
    headers = await login(
        client,
        "teacher.test",
        "Teacher123!",
    )

    response = await client.get(
        "/admin/users",
        headers=headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_student_cannot_list_admin_users(
    client,
    seeded_users,
):
    headers = await login(
        client,
        "student.test",
        "Student123!",
    )

    response = await client.get(
        "/admin/users",
        headers=headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_list_admin_users(
    client,
):
    response = await client.get(
        "/admin/users",
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_can_create_teacher_in_own_school(
    client,
    db_session,
    seeded_users,
):
    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        "/admin/users",
        headers=headers,
        json={
            "login_id": "teacher.created",
            "full_name": "Created Teacher",
            "role": "teacher",
            "password": "Teacher456!",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["login_id"] == "teacher.created"
    assert data["full_name"] == "Created Teacher"
    assert data["role"] == "teacher"
    assert data["school_id"] == seeded_users["school"].id
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data

    result = await db_session.execute(
        select(User).where(
            User.login_id == "teacher.created",
        )
    )

    created_user = result.scalar_one()

    assert (
        created_user.school_id
        == seeded_users["school"].id
    )
    assert created_user.role == UserRole.TEACHER
    assert created_user.password_hash != "Teacher456!"


@pytest.mark.asyncio
async def test_admin_can_create_student_in_own_school(
    client,
    db_session,
    seeded_users,
):
    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        "/admin/users",
        headers=headers,
        json={
            "login_id": "student.created",
            "full_name": "Created Student",
            "role": "student",
            "password": "Student456!",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["login_id"] == "student.created"
    assert data["full_name"] == "Created Student"
    assert data["role"] == "student"
    assert data["school_id"] == seeded_users["school"].id

    result = await db_session.execute(
        select(User).where(
            User.login_id == "student.created",
        )
    )

    created_user = result.scalar_one()

    assert (
        created_user.school_id
        == seeded_users["school"].id
    )
    assert created_user.role == UserRole.STUDENT


@pytest.mark.asyncio
async def test_admin_cannot_create_another_admin(
    client,
    seeded_users,
):
    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        "/admin/users",
        headers=headers,
        json={
            "login_id": "another.admin",
            "full_name": "Another Admin",
            "role": "admin",
            "password": "Admin456!",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_admin_cannot_create_duplicate_login_id(
    client,
    seeded_users,
):
    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        "/admin/users",
        headers=headers,
        json={
            "login_id": "teacher.test",
            "full_name": "Duplicate Teacher",
            "role": "teacher",
            "password": "Teacher456!",
        },
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_teacher_cannot_create_admin_user(
    client,
    seeded_users,
):
    headers = await login(
        client,
        "teacher.test",
        "Teacher123!",
    )

    response = await client.post(
        "/admin/users",
        headers=headers,
        json={
            "login_id": "blocked.student",
            "full_name": "Blocked Student",
            "role": "student",
            "password": "Student456!",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_student_cannot_create_admin_user(
    client,
    seeded_users,
):
    headers = await login(
        client,
        "student.test",
        "Student123!",
    )

    response = await client.post(
        "/admin/users",
        headers=headers,
        json={
            "login_id": "blocked.teacher",
            "full_name": "Blocked Teacher",
            "role": "teacher",
            "password": "Teacher456!",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_create_admin_user(
    client,
):
    response = await client.post(
        "/admin/users",
        json={
            "login_id": "blocked.student",
            "full_name": "Blocked Student",
            "role": "student",
            "password": "Student456!",
        },
    )

    assert response.status_code == 401

