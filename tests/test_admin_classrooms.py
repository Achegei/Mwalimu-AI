import pytest

from app.core.security import hash_password
from app.models.classroom import Classroom
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
async def test_admin_can_list_classrooms_in_own_school(
    client,
    seeded_users,
):
    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.get(
        "/admin/classrooms",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    classroom = seeded_users["classroom"]

    assert len(data) == 1
    assert data[0]["id"] == classroom.id
    assert data[0]["school_id"] == seeded_users["school"].id
    assert data[0]["teacher_id"] == seeded_users["teacher"].id
    assert data[0]["name"] == classroom.name
    assert data[0]["form_level"] == classroom.form_level
    assert data[0]["academic_year"] == classroom.academic_year


@pytest.mark.asyncio
async def test_admin_classroom_list_excludes_other_school(
    client,
    db_session,
    seeded_users,
):
    other_school = School(
        name="Foreign School",
        code="FOREIGN-CLASS-001",
        is_active=True,
    )

    db_session.add(other_school)
    await db_session.flush()

    foreign_teacher = User(
        school_id=other_school.id,
        login_id="foreign.class.teacher",
        full_name="Foreign Class Teacher",
        role=UserRole.TEACHER,
        password_hash=hash_password("Foreign123!"),
        is_active=True,
    )

    db_session.add(foreign_teacher)
    await db_session.flush()

    foreign_classroom = Classroom(
        school_id=other_school.id,
        teacher_id=foreign_teacher.id,
        name="Foreign Form 2",
        form_level=2,
        academic_year=2026,
    )

    db_session.add(foreign_classroom)
    await db_session.commit()

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.get(
        "/admin/classrooms",
        headers=headers,
    )

    assert response.status_code == 200

    classroom_ids = {
        item["id"]
        for item in response.json()
    }

    assert foreign_classroom.id not in classroom_ids


@pytest.mark.asyncio
async def test_admin_can_create_classroom_with_own_teacher(
    client,
    seeded_users,
):
    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    teacher = seeded_users["teacher"]

    response = await client.post(
        "/admin/classrooms",
        headers=headers,
        json={
            "name": "Form 3 East",
            "form_level": 3,
            "academic_year": 2026,
            "teacher_id": teacher.id,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["school_id"] == seeded_users["school"].id
    assert data["teacher_id"] == teacher.id
    assert data["name"] == "Form 3 East"
    assert data["form_level"] == 3
    assert data["academic_year"] == 2026


@pytest.mark.asyncio
async def test_admin_can_create_classroom_without_teacher(
    client,
    seeded_users,
):
    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        "/admin/classrooms",
        headers=headers,
        json={
            "name": "Form 4 West",
            "form_level": 4,
            "academic_year": 2026,
            "teacher_id": None,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["school_id"] == seeded_users["school"].id
    assert data["teacher_id"] is None


@pytest.mark.asyncio
async def test_admin_cannot_assign_foreign_school_teacher(
    client,
    db_session,
    seeded_users,
):
    other_school = School(
        name="Other Teacher School",
        code="OTHER-TEACHER-001",
        is_active=True,
    )

    db_session.add(other_school)
    await db_session.flush()

    foreign_teacher = User(
        school_id=other_school.id,
        login_id="foreign.assignment.teacher",
        full_name="Foreign Assignment Teacher",
        role=UserRole.TEACHER,
        password_hash=hash_password("Foreign123!"),
        is_active=True,
    )

    db_session.add(foreign_teacher)
    await db_session.commit()

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        "/admin/classrooms",
        headers=headers,
        json={
            "name": "Unsafe Classroom",
            "form_level": 2,
            "academic_year": 2026,
            "teacher_id": foreign_teacher.id,
        },
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_admin_cannot_assign_student_as_teacher(
    client,
    seeded_users,
):
    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    student = seeded_users["student"]

    response = await client.post(
        "/admin/classrooms",
        headers=headers,
        json={
            "name": "Invalid Teacher Classroom",
            "form_level": 2,
            "academic_year": 2026,
            "teacher_id": student.id,
        },
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_admin_cannot_create_duplicate_classroom(
    client,
    seeded_users,
):
    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    classroom = seeded_users["classroom"]

    response = await client.post(
        "/admin/classrooms",
        headers=headers,
        json={
            "name": classroom.name,
            "form_level": classroom.form_level,
            "academic_year": classroom.academic_year,
            "teacher_id": seeded_users["teacher"].id,
        },
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_teacher_cannot_manage_admin_classrooms(
    client,
    seeded_users,
):
    headers = await login(
        client,
        "teacher.test",
        "Teacher123!",
    )

    list_response = await client.get(
        "/admin/classrooms",
        headers=headers,
    )

    create_response = await client.post(
        "/admin/classrooms",
        headers=headers,
        json={
            "name": "Forbidden Classroom",
            "form_level": 2,
            "academic_year": 2026,
            "teacher_id": None,
        },
    )

    assert list_response.status_code == 403
    assert create_response.status_code == 403


@pytest.mark.asyncio
async def test_student_cannot_manage_admin_classrooms(
    client,
    seeded_users,
):
    headers = await login(
        client,
        "student.test",
        "Student123!",
    )

    response = await client.get(
        "/admin/classrooms",
        headers=headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_manage_admin_classrooms(
    client,
):
    list_response = await client.get(
        "/admin/classrooms",
    )

    create_response = await client.post(
        "/admin/classrooms",
        json={
            "name": "Unauthorized Classroom",
            "form_level": 2,
            "academic_year": 2026,
            "teacher_id": None,
        },
    )

    assert list_response.status_code == 401
    assert create_response.status_code == 401
