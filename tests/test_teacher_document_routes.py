from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.classroom import Classroom
from app.models.content import Subject, Topic
from app.models.document import Document
from app.models.enums import (
    DocumentScope,
    UserRole,
)
from app.models.teaching_assignment import TeachingAssignment
from app.models.user import User
from app.core.security import hash_password


async def create_teacher(
    db: AsyncSession,
    *,
    school_id: int,
    login_id: str,
    full_name: str,
) -> User:
    teacher = User(
        school_id=school_id,
        login_id=login_id,
        full_name=full_name,
        role=UserRole.TEACHER,
        password_hash=hash_password("Teacher123!"),
        is_active=True,
    )

    db.add(teacher)
    await db.flush()

    return teacher


async def login(
    client,
    *,
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

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }


async def create_assignment_fixture(
    db: AsyncSession,
    *,
    school_id: int,
    teacher_id: int,
    suffix: str,
    is_active: bool = True,
):
    subject = Subject(
        school_id=school_id,
        name=f"Biology {suffix}",
        slug=f"biology-{suffix}",
        description="Biology",
        is_active=True,
    )

    db.add(subject)
    await db.flush()

    classroom = Classroom(
        school_id=school_id,
        name=f"Form 2 {suffix}",
        form_level=2,
        academic_year=2026,
    )

    db.add(classroom)
    await db.flush()

    topic = Topic(
        subject_id=subject.id,
        title=f"Cells {suffix}",
        slug=f"cells-{suffix}",
        form_level=2,
        order_index=1,
        is_active=True,
    )

    db.add(topic)
    await db.flush()

    assignment = TeachingAssignment(
        school_id=school_id,
        teacher_id=teacher_id,
        subject_id=subject.id,
        classroom_id=classroom.id,
        is_active=is_active,
    )

    db.add(assignment)
    await db.flush()

    return subject, classroom, topic, assignment


@pytest.mark.asyncio
async def test_teacher_can_upload_assignment_document_via_api(
    client,
    db_session,
    seeded_users,
    monkeypatch,
    tmp_path,
):
    teacher = seeded_users["teacher"]
    school = seeded_users["school"]

    subject, classroom, topic, assignment = (
        await create_assignment_fixture(
            db_session,
            school_id=school.id,
            teacher_id=teacher.id,
            suffix="upload",
        )
    )

    await db_session.commit()

    monkeypatch.setenv(
        "DOCUMENT_STORAGE_ROOT",
        str(tmp_path),
    )

    headers = await login(
        client,
        login_id=teacher.login_id,
        password="Teacher123!",
    )

    response = await client.post(
        "/teacher/documents",
        headers=headers,
        data={
            "teaching_assignment_id": str(
                assignment.id
            ),
            "title": "Cell Structure Notes",
            "document_type": "teacher_notes",
            "topic_id": str(topic.id),
            "academic_year": "2026",
        },
        files={
            "file": (
                "cell-notes.txt",
                b"Cell membrane and nucleus notes.",
                "text/plain",
            ),
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["school_id"] == school.id
    assert data["subject_id"] == subject.id
    assert data["topic_id"] == topic.id
    assert (
        data["scope"]
        == DocumentScope.TEACHING_ASSIGNMENT.value
    )
    assert (
        data["teaching_assignment_id"]
        == assignment.id
    )
    assert data["uploaded_by_id"] == teacher.id
    assert data["form_level"] == classroom.form_level
    assert data["title"] == "Cell Structure Notes"

    result = await db_session.execute(
        select(Document).where(
            Document.id == data["id"]
        )
    )

    document = result.scalar_one()

    assert (
        document.scope
        == DocumentScope.TEACHING_ASSIGNMENT
    )
    assert (
        document.teaching_assignment_id
        == assignment.id
    )
    assert document.subject_id == subject.id
    assert document.form_level == classroom.form_level
    assert document.uploaded_by_id == teacher.id


@pytest.mark.asyncio
async def test_teacher_cannot_upload_to_another_teachers_assignment(
    client,
    db_session,
    seeded_users,
    monkeypatch,
    tmp_path,
):
    teacher = seeded_users["teacher"]
    school = seeded_users["school"]

    other_teacher = await create_teacher(
        db_session,
        school_id=school.id,
        login_id="other.teacher.documents",
        full_name="Other Teacher",
    )

    _, _, topic, assignment = (
        await create_assignment_fixture(
            db_session,
            school_id=school.id,
            teacher_id=other_teacher.id,
            suffix="foreign",
        )
    )

    await db_session.commit()

    monkeypatch.setenv(
        "DOCUMENT_STORAGE_ROOT",
        str(tmp_path),
    )

    headers = await login(
        client,
        login_id=teacher.login_id,
        password="Teacher123!",
    )

    response = await client.post(
        "/teacher/documents",
        headers=headers,
        data={
            "teaching_assignment_id": str(
                assignment.id
            ),
            "title": "Unauthorized Notes",
            "document_type": "teacher_notes",
            "topic_id": str(topic.id),
        },
        files={
            "file": (
                "unauthorized.txt",
                b"Should never be stored.",
                "text/plain",
            ),
        },
    )

    assert response.status_code == 400

    assert (
        response.json()["detail"]
        == "Active teaching assignment not found for this teacher."
    )

    result = await db_session.execute(
        select(Document).where(
            Document.teaching_assignment_id
            == assignment.id
        )
    )

    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_inactive_assignment_cannot_upload_document_via_api(
    client,
    db_session,
    seeded_users,
    monkeypatch,
    tmp_path,
):
    teacher = seeded_users["teacher"]
    school = seeded_users["school"]

    _, _, topic, assignment = (
        await create_assignment_fixture(
            db_session,
            school_id=school.id,
            teacher_id=teacher.id,
            suffix="inactive",
            is_active=False,
        )
    )

    await db_session.commit()

    monkeypatch.setenv(
        "DOCUMENT_STORAGE_ROOT",
        str(tmp_path),
    )

    headers = await login(
        client,
        login_id=teacher.login_id,
        password="Teacher123!",
    )

    response = await client.post(
        "/teacher/documents",
        headers=headers,
        data={
            "teaching_assignment_id": str(
                assignment.id
            ),
            "title": "Inactive Notes",
            "document_type": "teacher_notes",
            "topic_id": str(topic.id),
        },
        files={
            "file": (
                "inactive.txt",
                b"Inactive assignment.",
                "text/plain",
            ),
        },
    )

    assert response.status_code == 400

    assert (
        response.json()["detail"]
        == "Active teaching assignment not found for this teacher."
    )


@pytest.mark.asyncio
async def test_teacher_upload_rejects_wrong_subject_topic(
    client,
    db_session,
    seeded_users,
    monkeypatch,
    tmp_path,
):
    teacher = seeded_users["teacher"]
    school = seeded_users["school"]

    _, _, _, assignment = (
        await create_assignment_fixture(
            db_session,
            school_id=school.id,
            teacher_id=teacher.id,
            suffix="correct",
        )
    )

    _, _, wrong_topic, _ = (
        await create_assignment_fixture(
            db_session,
            school_id=school.id,
            teacher_id=teacher.id,
            suffix="wrong",
        )
    )

    await db_session.commit()

    monkeypatch.setenv(
        "DOCUMENT_STORAGE_ROOT",
        str(tmp_path),
    )

    headers = await login(
        client,
        login_id=teacher.login_id,
        password="Teacher123!",
    )

    response = await client.post(
        "/teacher/documents",
        headers=headers,
        data={
            "teaching_assignment_id": str(
                assignment.id
            ),
            "title": "Wrong Topic Notes",
            "document_type": "teacher_notes",
            "topic_id": str(wrong_topic.id),
        },
        files={
            "file": (
                "wrong-topic.txt",
                b"Wrong topic.",
                "text/plain",
            ),
        },
    )

    assert response.status_code == 400

    assert (
        response.json()["detail"]
        == "Active topic not found for this teaching assignment."
    )


@pytest.mark.asyncio
async def test_teacher_upload_rejects_empty_file(
    client,
    db_session,
    seeded_users,
):
    teacher = seeded_users["teacher"]
    school = seeded_users["school"]

    _, _, _, assignment = (
        await create_assignment_fixture(
            db_session,
            school_id=school.id,
            teacher_id=teacher.id,
            suffix="empty",
        )
    )

    await db_session.commit()

    headers = await login(
        client,
        login_id=teacher.login_id,
        password="Teacher123!",
    )

    response = await client.post(
        "/teacher/documents",
        headers=headers,
        data={
            "teaching_assignment_id": str(
                assignment.id
            ),
            "title": "Empty Notes",
            "document_type": "teacher_notes",
        },
        files={
            "file": (
                "empty.txt",
                b"",
                "text/plain",
            ),
        },
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Document file cannot be empty."
    )


@pytest.mark.asyncio
async def test_student_cannot_upload_teacher_document(
    client,
    db_session,
    seeded_users,
):
    student = seeded_users["student"]
    school = seeded_users["school"]
    teacher = seeded_users["teacher"]

    _, _, _, assignment = (
        await create_assignment_fixture(
            db_session,
            school_id=school.id,
            teacher_id=teacher.id,
            suffix="student-denied",
        )
    )

    await db_session.commit()

    headers = await login(
        client,
        login_id=student.login_id,
        password="Student123!",
    )

    response = await client.post(
        "/teacher/documents",
        headers=headers,
        data={
            "teaching_assignment_id": str(
                assignment.id
            ),
            "title": "Student Upload",
            "document_type": "teacher_notes",
        },
        files={
            "file": (
                "student.txt",
                b"Not allowed.",
                "text/plain",
            ),
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_upload_teacher_document(
    client,
):
    response = await client.post(
        "/teacher/documents",
        data={
            "teaching_assignment_id": "1",
            "title": "Anonymous Upload",
            "document_type": "teacher_notes",
        },
        files={
            "file": (
                "anonymous.txt",
                b"Not allowed.",
                "text/plain",
            ),
        },
    )

    assert response.status_code in {401, 403}
