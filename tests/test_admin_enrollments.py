import pytest

from app.core.security import hash_password
from app.models.classroom import Classroom
from app.models.enrollment import Enrollment
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
async def test_admin_can_list_students_in_own_classroom(
    client,
    seeded_users,
):
    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    classroom = seeded_users["classroom"]
    student = seeded_users["student"]

    response = await client.get(
        f"/admin/classrooms/{classroom.id}/students",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["student_id"] == student.id
    assert data[0]["login_id"] == student.login_id
    assert data[0]["full_name"] == student.full_name
    assert data[0]["is_active"] is True


@pytest.mark.asyncio
async def test_admin_can_enroll_student_in_own_classroom(
    client,
    db_session,
    seeded_users,
):
    school = seeded_users["school"]
    classroom = seeded_users["classroom"]

    student = User(
        school_id=school.id,
        login_id="student.second",
        full_name="Second Student",
        role=UserRole.STUDENT,
        password_hash=hash_password(
            "Student123!"
        ),
        is_active=True,
    )

    db_session.add(student)
    await db_session.commit()
    await db_session.refresh(student)

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        (
            f"/admin/classrooms/{classroom.id}"
            f"/students/{student.id}"
        ),
        headers=headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["student_id"] == student.id
    assert data["login_id"] == student.login_id
    assert data["full_name"] == student.full_name
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_admin_cannot_enroll_foreign_school_student(
    client,
    db_session,
    seeded_users,
):
    other_school = School(
        name="Foreign Secondary School",
        code="FOREIGN-ENROLL-001",
        is_active=True,
    )

    db_session.add(other_school)
    await db_session.flush()

    foreign_student = User(
        school_id=other_school.id,
        login_id="foreign.enrollment.student",
        full_name="Foreign Enrollment Student",
        role=UserRole.STUDENT,
        password_hash=hash_password(
            "Foreign123!"
        ),
        is_active=True,
    )

    db_session.add(foreign_student)
    await db_session.commit()
    await db_session.refresh(foreign_student)

    classroom = seeded_users["classroom"]

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        (
            f"/admin/classrooms/{classroom.id}"
            f"/students/{foreign_student.id}"
        ),
        headers=headers,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_admin_cannot_manage_foreign_school_classroom(
    client,
    db_session,
    seeded_users,
):
    other_school = School(
        name="Foreign Classroom School",
        code="FOREIGN-CLASS-001",
        is_active=True,
    )

    db_session.add(other_school)
    await db_session.flush()

    foreign_classroom = Classroom(
        school_id=other_school.id,
        teacher_id=None,
        name="Foreign Form 2",
        form_level=2,
        academic_year=2026,
    )

    db_session.add(foreign_classroom)
    await db_session.commit()
    await db_session.refresh(foreign_classroom)

    student = seeded_users["student"]

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    list_response = await client.get(
        (
            f"/admin/classrooms/{foreign_classroom.id}"
            "/students"
        ),
        headers=headers,
    )

    enroll_response = await client.post(
        (
            f"/admin/classrooms/{foreign_classroom.id}"
            f"/students/{student.id}"
        ),
        headers=headers,
    )

    assert list_response.status_code == 404
    assert enroll_response.status_code == 400


@pytest.mark.asyncio
async def test_admin_cannot_enroll_teacher_as_student(
    client,
    seeded_users,
):
    classroom = seeded_users["classroom"]
    teacher = seeded_users["teacher"]

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        (
            f"/admin/classrooms/{classroom.id}"
            f"/students/{teacher.id}"
        ),
        headers=headers,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_admin_cannot_duplicate_student_enrollment(
    client,
    seeded_users,
):
    classroom = seeded_users["classroom"]
    student = seeded_users["student"]

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        (
            f"/admin/classrooms/{classroom.id}"
            f"/students/{student.id}"
        ),
        headers=headers,
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_inactive_student_cannot_be_enrolled(
    client,
    db_session,
    seeded_users,
):
    school = seeded_users["school"]
    classroom = seeded_users["classroom"]

    student = User(
        school_id=school.id,
        login_id="inactive.student",
        full_name="Inactive Student",
        role=UserRole.STUDENT,
        password_hash=hash_password(
            "Student123!"
        ),
        is_active=False,
    )

    db_session.add(student)
    await db_session.commit()
    await db_session.refresh(student)

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        (
            f"/admin/classrooms/{classroom.id}"
            f"/students/{student.id}"
        ),
        headers=headers,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_teacher_cannot_manage_admin_enrollments(
    client,
    seeded_users,
):
    classroom = seeded_users["classroom"]
    student = seeded_users["student"]

    headers = await login(
        client,
        "teacher.test",
        "Teacher123!",
    )

    list_response = await client.get(
        f"/admin/classrooms/{classroom.id}/students",
        headers=headers,
    )

    enroll_response = await client.post(
        (
            f"/admin/classrooms/{classroom.id}"
            f"/students/{student.id}"
        ),
        headers=headers,
    )

    assert list_response.status_code == 403
    assert enroll_response.status_code == 403


@pytest.mark.asyncio
async def test_student_cannot_manage_admin_enrollments(
    client,
    seeded_users,
):
    classroom = seeded_users["classroom"]
    student = seeded_users["student"]

    headers = await login(
        client,
        "student.test",
        "Student123!",
    )

    list_response = await client.get(
        f"/admin/classrooms/{classroom.id}/students",
        headers=headers,
    )

    enroll_response = await client.post(
        (
            f"/admin/classrooms/{classroom.id}"
            f"/students/{student.id}"
        ),
        headers=headers,
    )

    assert list_response.status_code == 403
    assert enroll_response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_manage_admin_enrollments(
    client,
    seeded_users,
):
    classroom = seeded_users["classroom"]
    student = seeded_users["student"]

    list_response = await client.get(
        f"/admin/classrooms/{classroom.id}/students",
    )

    enroll_response = await client.post(
        (
            f"/admin/classrooms/{classroom.id}"
            f"/students/{student.id}"
        ),
    )

    assert list_response.status_code == 401
    assert enroll_response.status_code == 401
