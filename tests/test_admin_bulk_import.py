import io

import pytest
from openpyxl import Workbook
from sqlalchemy import select

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


def csv_upload(rows: list[str]):
    content = (
        "full_name,login_id,password\n"
        + "\n".join(rows)
        + "\n"
    ).encode()

    return {
        "file": (
            "students.csv",
            content,
            "text/csv",
        ),
    }


def xlsx_upload(rows: list[tuple[str, str, str]]):
    workbook = Workbook()
    worksheet = workbook.active

    worksheet.append(
        [
            "full_name",
            "login_id",
            "password",
        ]
    )

    for row in rows:
        worksheet.append(row)

    buffer = io.BytesIO()
    workbook.save(buffer)

    return {
        "file": (
            "students.xlsx",
            buffer.getvalue(),
            (
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        ),
    }


@pytest.mark.asyncio
async def test_admin_can_bulk_import_csv_students(
    client,
    db_session,
    seeded_users,
):
    classroom = seeded_users["classroom"]

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        (
            f"/admin/classrooms/{classroom.id}"
            "/students/import"
        ),
        headers=headers,
        files=csv_upload(
            [
                "Jane Wanjiku,jane.wanjiku,TempPass123!",
                "Brian Otieno,brian.otieno,TempPass123!",
            ]
        ),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_rows"] == 2
    assert data["created"] == 2
    assert data["enrolled"] == 2
    assert data["skipped"] == 0
    assert data["failed"] == 0
    assert len(data["rows"]) == 2

    result = await db_session.execute(
        select(User).where(
            User.login_id.in_(
                [
                    "jane.wanjiku",
                    "brian.otieno",
                ]
            )
        )
    )

    users = list(result.scalars().all())

    assert len(users) == 2

    for user in users:
        assert user.school_id == seeded_users["school"].id
        assert user.role == UserRole.STUDENT

        enrollment_result = await db_session.execute(
            select(Enrollment).where(
                Enrollment.classroom_id == classroom.id,
                Enrollment.student_id == user.id,
                Enrollment.is_active.is_(True),
            )
        )

        assert (
            enrollment_result.scalar_one_or_none()
            is not None
        )


@pytest.mark.asyncio
async def test_admin_can_bulk_import_xlsx_students(
    client,
    db_session,
    seeded_users,
):
    classroom = seeded_users["classroom"]

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        (
            f"/admin/classrooms/{classroom.id}"
            "/students/import"
        ),
        headers=headers,
        files=xlsx_upload(
            [
                (
                    "Mary Akinyi",
                    "mary.akinyi",
                    "TempPass123!",
                ),
                (
                    "Peter Kamau",
                    "peter.kamau",
                    "TempPass123!",
                ),
            ]
        ),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_rows"] == 2
    assert data["created"] == 2
    assert data["enrolled"] == 2
    assert data["skipped"] == 0
    assert data["failed"] == 0

    result = await db_session.execute(
        select(User).where(
            User.login_id == "mary.akinyi"
        )
    )

    user = result.scalar_one()

    assert user.school_id == seeded_users["school"].id
    assert user.role == UserRole.STUDENT


@pytest.mark.asyncio
async def test_bulk_import_reuses_existing_school_student(
    client,
    db_session,
    seeded_users,
):
    school = seeded_users["school"]
    classroom = seeded_users["classroom"]

    existing_student = User(
        school_id=school.id,
        login_id="existing.student",
        full_name="Existing Student",
        role=UserRole.STUDENT,
        password_hash=hash_password(
            "Existing123!"
        ),
        is_active=True,
    )

    db_session.add(existing_student)
    await db_session.commit()
    await db_session.refresh(existing_student)

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        (
            f"/admin/classrooms/{classroom.id}"
            "/students/import"
        ),
        headers=headers,
        files=csv_upload(
            [
                (
                    "Existing Student,"
                    "existing.student,"
                    "Ignored123!"
                ),
            ]
        ),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_rows"] == 1
    assert data["created"] == 0
    assert data["enrolled"] == 1
    assert data["skipped"] == 0
    assert data["failed"] == 0

    enrollment_result = await db_session.execute(
        select(Enrollment).where(
            Enrollment.classroom_id == classroom.id,
            Enrollment.student_id == existing_student.id,
            Enrollment.is_active.is_(True),
        )
    )

    assert enrollment_result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_bulk_import_skips_already_enrolled_student(
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
            "/students/import"
        ),
        headers=headers,
        files=csv_upload(
            [
                (
                    f"{student.full_name},"
                    f"{student.login_id},"
                    "Ignored123!"
                ),
            ]
        ),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_rows"] == 1
    assert data["created"] == 0
    assert data["enrolled"] == 0
    assert data["skipped"] == 1
    assert data["failed"] == 0


@pytest.mark.asyncio
async def test_bulk_import_reports_partial_row_failures(
    client,
    db_session,
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
            "/students/import"
        ),
        headers=headers,
        files=csv_upload(
            [
                "Valid Student,valid.student,TempPass123!",
                (
                    "Teacher Collision,"
                    f"{teacher.login_id},"
                    "TempPass123!"
                ),
                "Missing Password,missing.password,",
            ]
        ),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_rows"] == 3
    assert data["created"] == 1
    assert data["enrolled"] == 1
    assert data["skipped"] == 0
    assert data["failed"] == 2

    statuses = [
        row["status"]
        for row in data["rows"]
    ]

    assert statuses == [
        "enrolled",
        "failed",
        "failed",
    ]

    result = await db_session.execute(
        select(User).where(
            User.login_id == "valid.student"
        )
    )

    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_bulk_import_rejects_foreign_login_id_collision(
    client,
    db_session,
    seeded_users,
):
    other_school = School(
        name="Bulk Foreign School",
        code="BULK-FOREIGN-001",
        is_active=True,
    )

    db_session.add(other_school)
    await db_session.flush()

    foreign_student = User(
        school_id=other_school.id,
        login_id="foreign.bulk.student",
        full_name="Foreign Bulk Student",
        role=UserRole.STUDENT,
        password_hash=hash_password(
            "Foreign123!"
        ),
        is_active=True,
    )

    db_session.add(foreign_student)
    await db_session.commit()

    classroom = seeded_users["classroom"]

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        (
            f"/admin/classrooms/{classroom.id}"
            "/students/import"
        ),
        headers=headers,
        files=csv_upload(
            [
                (
                    "Foreign Bulk Student,"
                    "foreign.bulk.student,"
                    "TempPass123!"
                ),
            ]
        ),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["created"] == 0
    assert data["enrolled"] == 0
    assert data["skipped"] == 0
    assert data["failed"] == 1
    assert data["rows"][0]["status"] == "failed"


@pytest.mark.asyncio
async def test_bulk_import_rejects_foreign_classroom(
    client,
    db_session,
    seeded_users,
):
    other_school = School(
        name="Bulk Classroom School",
        code="BULK-CLASS-001",
        is_active=True,
    )

    db_session.add(other_school)
    await db_session.flush()

    classroom = Classroom(
        school_id=other_school.id,
        name="Foreign Bulk Classroom",
        form_level=2,
        academic_year=2026,
    )

    db_session.add(classroom)
    await db_session.commit()
    await db_session.refresh(classroom)

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        (
            f"/admin/classrooms/{classroom.id}"
            "/students/import"
        ),
        headers=headers,
        files=csv_upload(
            [
                "Valid Student,valid.student,TempPass123!",
            ]
        ),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_bulk_import_rejects_missing_required_columns(
    client,
    seeded_users,
):
    classroom = seeded_users["classroom"]

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    content = (
        "full_name,login_id\n"
        "Jane Wanjiku,jane.wanjiku\n"
    ).encode()

    response = await client.post(
        (
            f"/admin/classrooms/{classroom.id}"
            "/students/import"
        ),
        headers=headers,
        files={
            "file": (
                "students.csv",
                content,
                "text/csv",
            ),
        },
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_bulk_import_rejects_unsupported_file_type(
    client,
    seeded_users,
):
    classroom = seeded_users["classroom"]

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        (
            f"/admin/classrooms/{classroom.id}"
            "/students/import"
        ),
        headers=headers,
        files={
            "file": (
                "students.txt",
                b"not a supported import",
                "text/plain",
            ),
        },
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_teacher_cannot_bulk_import_students(
    client,
    seeded_users,
):
    classroom = seeded_users["classroom"]

    headers = await login(
        client,
        "teacher.test",
        "Teacher123!",
    )

    response = await client.post(
        (
            f"/admin/classrooms/{classroom.id}"
            "/students/import"
        ),
        headers=headers,
        files=csv_upload(
            [
                "Jane Wanjiku,jane.wanjiku,TempPass123!",
            ]
        ),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_student_cannot_bulk_import_students(
    client,
    seeded_users,
):
    classroom = seeded_users["classroom"]

    headers = await login(
        client,
        "student.test",
        "Student123!",
    )

    response = await client.post(
        (
            f"/admin/classrooms/{classroom.id}"
            "/students/import"
        ),
        headers=headers,
        files=csv_upload(
            [
                "Jane Wanjiku,jane.wanjiku,TempPass123!",
            ]
        ),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_bulk_import_students(
    client,
    seeded_users,
):
    classroom = seeded_users["classroom"]

    response = await client.post(
        (
            f"/admin/classrooms/{classroom.id}"
            "/students/import"
        ),
        files=csv_upload(
            [
                "Jane Wanjiku,jane.wanjiku,TempPass123!",
            ]
        ),
    )

    assert response.status_code == 401
