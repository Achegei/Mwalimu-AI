from pathlib import Path

import pytest

from app.core.security import hash_password
from app.models.content import Subject, Topic
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


async def create_subject_and_topic(
    db_session,
    school_id: int,
    *,
    subject_name: str = "Mathematics",
    subject_slug: str = "mathematics",
    topic_title: str = "Algebra",
    topic_slug: str = "algebra",
    form_level: int = 2,
):
    subject = Subject(
        school_id=school_id,
        name=subject_name,
        slug=subject_slug,
        description=None,
        is_active=True,
    )

    db_session.add(subject)
    await db_session.flush()

    topic = Topic(
        subject_id=subject.id,
        slug=topic_slug,
        title=topic_title,
        summary=None,
        form_level=form_level,
        order_index=1,
        is_active=True,
    )

    db_session.add(topic)
    await db_session.commit()
    await db_session.refresh(subject)
    await db_session.refresh(topic)

    return subject, topic


@pytest.mark.asyncio
async def test_admin_can_upload_document_for_own_school(
    client,
    db_session,
    seeded_users,
    tmp_path,
    monkeypatch,
):
    school = seeded_users["school"]

    subject, topic = await create_subject_and_topic(
        db_session,
        school.id,
    )

    monkeypatch.setenv(
        "DOCUMENT_STORAGE_PATH",
        str(tmp_path),
    )

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        "/admin/documents",
        headers=headers,
        data={
            "title": "Form 2 Algebra Notes",
            "document_type": "teacher_notes",
            "subject_id": str(subject.id),
            "topic_id": str(topic.id),
            "form_level": "2",
        },
        files={
            "file": (
                "algebra-notes.pdf",
                b"%PDF-1.4 test document",
                "application/pdf",
            ),
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["school_id"] == school.id
    assert data["subject_id"] == subject.id
    assert data["topic_id"] == topic.id
    assert data["title"] == "Form 2 Algebra Notes"
    assert data["document_type"] == "teacher_notes"
    assert data["form_level"] == 2
    assert data["original_filename"] == "algebra-notes.pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["file_size"] > 0
    assert data["processing_status"] == "uploaded"
    assert data["is_active"] is True

    storage_key = data["storage_key"]

    assert storage_key
    assert not Path(storage_key).is_absolute()


@pytest.mark.asyncio
async def test_admin_can_upload_past_paper_metadata(
    client,
    db_session,
    seeded_users,
    tmp_path,
    monkeypatch,
):
    school = seeded_users["school"]

    subject, _ = await create_subject_and_topic(
        db_session,
        school.id,
        subject_name="Chemistry",
        subject_slug="chemistry",
        topic_title="Acids and Bases",
        topic_slug="acids-and-bases",
        form_level=4,
    )

    monkeypatch.setenv(
        "DOCUMENT_STORAGE_PATH",
        str(tmp_path),
    )

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        "/admin/documents",
        headers=headers,
        data={
            "title": "Chemistry Paper 2 2025",
            "document_type": "past_paper",
            "subject_id": str(subject.id),
            "form_level": "4",
            "exam_year": "2025",
            "paper_number": "2",
        },
        files={
            "file": (
                "chemistry-paper-2-2025.pdf",
                b"%PDF-1.4 past paper",
                "application/pdf",
            ),
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["document_type"] == "past_paper"
    assert data["exam_year"] == 2025
    assert data["paper_number"] == "2"
    assert data["topic_id"] is None


@pytest.mark.asyncio
async def test_admin_lists_only_own_school_documents(
    client,
    db_session,
    seeded_users,
    tmp_path,
    monkeypatch,
):
    school = seeded_users["school"]

    subject, _ = await create_subject_and_topic(
        db_session,
        school.id,
    )

    monkeypatch.setenv(
        "DOCUMENT_STORAGE_PATH",
        str(tmp_path),
    )

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    upload_response = await client.post(
        "/admin/documents",
        headers=headers,
        data={
            "title": "Own School Mathematics",
            "document_type": "textbook",
            "subject_id": str(subject.id),
            "form_level": "2",
        },
        files={
            "file": (
                "mathematics.pdf",
                b"%PDF-1.4 mathematics",
                "application/pdf",
            ),
        },
    )

    assert upload_response.status_code == 201

    response = await client.get(
        "/admin/documents",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["school_id"] == school.id
    assert data[0]["title"] == "Own School Mathematics"


@pytest.mark.asyncio
async def test_admin_cannot_upload_to_foreign_school_subject(
    client,
    db_session,
    seeded_users,
    tmp_path,
    monkeypatch,
):
    other_school = School(
        name="Foreign Document School",
        code="FOREIGN-DOC-001",
        is_active=True,
    )

    db_session.add(other_school)
    await db_session.flush()

    subject, _ = await create_subject_and_topic(
        db_session,
        other_school.id,
        subject_name="Biology",
        subject_slug="foreign-biology",
        topic_title="Cells",
        topic_slug="foreign-cells",
    )

    monkeypatch.setenv(
        "DOCUMENT_STORAGE_PATH",
        str(tmp_path),
    )

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        "/admin/documents",
        headers=headers,
        data={
            "title": "Foreign Biology",
            "document_type": "textbook",
            "subject_id": str(subject.id),
            "form_level": "2",
        },
        files={
            "file": (
                "biology.pdf",
                b"%PDF-1.4 biology",
                "application/pdf",
            ),
        },
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_admin_cannot_use_topic_from_different_subject(
    client,
    db_session,
    seeded_users,
    tmp_path,
    monkeypatch,
):
    school = seeded_users["school"]

    mathematics, _ = await create_subject_and_topic(
        db_session,
        school.id,
    )

    _, biology_topic = await create_subject_and_topic(
        db_session,
        school.id,
        subject_name="Biology",
        subject_slug="biology",
        topic_title="Cells",
        topic_slug="cells",
    )

    monkeypatch.setenv(
        "DOCUMENT_STORAGE_PATH",
        str(tmp_path),
    )

    headers = await login(
        client,
        "admin.test",
        "Admin123!",
    )

    response = await client.post(
        "/admin/documents",
        headers=headers,
        data={
            "title": "Invalid Topic Mapping",
            "document_type": "teacher_notes",
            "subject_id": str(mathematics.id),
            "topic_id": str(biology_topic.id),
            "form_level": "2",
        },
        files={
            "file": (
                "notes.pdf",
                b"%PDF-1.4 notes",
                "application/pdf",
            ),
        },
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_teacher_cannot_manage_admin_documents(
    client,
    seeded_users,
):
    headers = await login(
        client,
        "teacher.test",
        "Teacher123!",
    )

    response = await client.get(
        "/admin/documents",
        headers=headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_student_cannot_manage_admin_documents(
    client,
    seeded_users,
):
    headers = await login(
        client,
        "student.test",
        "Student123!",
    )

    response = await client.get(
        "/admin/documents",
        headers=headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_manage_admin_documents(
    client,
):
    response = await client.get(
        "/admin/documents",
    )

    assert response.status_code == 401
