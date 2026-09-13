import pytest

from app.models.content import Subject, Topic


@pytest.mark.asyncio
async def test_student_can_list_subjects(
    client,
    db_session,
    seeded_users,
):
    subject = Subject(
        name="Biology",
        slug="biology",
        description="Form 2 Biology",
        is_active=True,
    )

    db_session.add(subject)
    await db_session.commit()

    login_response = await client.post(
        "/auth/login",
        json={
            "login_id": "student.test",
            "password": "Student123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = await client.get(
        "/student/subjects",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["name"] == "Biology"
    assert data[0]["slug"] == "biology"


@pytest.mark.asyncio
async def test_student_can_list_topics_for_subject(
    client,
    db_session,
    seeded_users,
):
    subject = Subject(
        name="Biology",
        slug="biology",
        description="Form 2 Biology",
        is_active=True,
    )

    db_session.add(subject)
    await db_session.flush()

    topic = Topic(
        subject_id=subject.id,
        slug="transport-in-plants-and-animals",
        title="Transport in Plants and Animals",
        summary="Transport processes in plants and animals.",
        form_level=2,
        order_index=1,
        is_active=True,
    )

    db_session.add(topic)
    await db_session.commit()

    login_response = await client.post(
        "/auth/login",
        json={
            "login_id": "student.test",
            "password": "Student123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = await client.get(
        f"/student/subjects/{subject.id}/topics",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == subject.id
    assert data["name"] == "Biology"
    assert data["slug"] == "biology"

    assert len(data["topics"]) == 1

    topic_data = data["topics"][0]

    assert topic_data["title"] == "Transport in Plants and Animals"
    assert topic_data["slug"] == "transport-in-plants-and-animals"
    assert topic_data["form_level"] == 2


@pytest.mark.asyncio
async def test_teacher_cannot_access_student_subjects(
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
        "/student/subjects",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_access_student_subjects(
    client,
):
    response = await client.get(
        "/student/subjects",
    )

    assert response.status_code == 401
