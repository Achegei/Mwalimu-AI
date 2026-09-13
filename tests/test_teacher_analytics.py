import pytest

from app.models.assessment import AssessmentAttempt
from app.models.content import Subject, Topic
from app.models.enums import (
    AssessmentStatus,
    AssessmentType,
)


@pytest.fixture
async def teacher_analytics_data(
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

    topic_1 = Topic(
        subject_id=subject.id,
        slug="transport-in-plants-and-animals",
        title="Transport in Plants and Animals",
        summary="Transport processes in plants and animals.",
        form_level=2,
        order_index=1,
        is_active=True,
    )

    topic_2 = Topic(
        subject_id=subject.id,
        slug="gaseous-exchange",
        title="Gaseous Exchange",
        summary="Exchange of gases in living organisms.",
        form_level=2,
        order_index=2,
        is_active=True,
    )

    topic_3 = Topic(
        subject_id=subject.id,
        slug="respiration",
        title="Respiration",
        summary="Release of energy from food.",
        form_level=2,
        order_index=3,
        is_active=True,
    )

    db_session.add_all(
        [
            topic_1,
            topic_2,
            topic_3,
        ]
    )

    await db_session.flush()

    student = seeded_users["student"]
    classroom = seeded_users["classroom"]

    attempts = [
        AssessmentAttempt(
            student_id=student.id,
            classroom_id=classroom.id,
            topic_id=topic_1.id,
            assessment_type=AssessmentType.DIAGNOSTIC,
            status=AssessmentStatus.COMPLETED,
            correct_answers=1,
            total_questions=3,
            score_percentage=40.0,
        ),
        AssessmentAttempt(
            student_id=student.id,
            classroom_id=classroom.id,
            topic_id=topic_1.id,
            assessment_type=AssessmentType.PRACTICE,
            status=AssessmentStatus.COMPLETED,
            correct_answers=2,
            total_questions=3,
            score_percentage=70.0,
        ),
        AssessmentAttempt(
            student_id=student.id,
            classroom_id=classroom.id,
            topic_id=topic_2.id,
            assessment_type=AssessmentType.DIAGNOSTIC,
            status=AssessmentStatus.COMPLETED,
            correct_answers=2,
            total_questions=3,
            score_percentage=65.0,
        ),
        AssessmentAttempt(
            student_id=student.id,
            classroom_id=classroom.id,
            topic_id=topic_2.id,
            assessment_type=AssessmentType.PRACTICE,
            status=AssessmentStatus.COMPLETED,
            correct_answers=3,
            total_questions=3,
            score_percentage=80.0,
        ),
    ]

    db_session.add_all(attempts)
    await db_session.commit()

    return {
        "subject": subject,
        "topic_1": topic_1,
        "topic_2": topic_2,
        "topic_3": topic_3,
        "attempts": attempts,
    }


async def teacher_headers(client):
    response = await client.post(
        "/auth/login",
        json={
            "login_id": "teacher.test",
            "password": "Teacher123!",
        },
    )

    assert response.status_code == 200

    return {
        "Authorization": (
            f"Bearer {response.json()['access_token']}"
        ),
    }


async def student_headers(client):
    response = await client.post(
        "/auth/login",
        json={
            "login_id": "student.test",
            "password": "Student123!",
        },
    )

    assert response.status_code == 200

    return {
        "Authorization": (
            f"Bearer {response.json()['access_token']}"
        ),
    }


@pytest.mark.asyncio
async def test_teacher_lists_own_classes(
    client,
    seeded_users,
):
    headers = await teacher_headers(client)

    response = await client.get(
        "/teacher/classes",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1

    classroom = data[0]

    assert classroom["id"] == seeded_users["classroom"].id
    assert classroom["name"] == "Form 2 Test"
    assert classroom["form_level"] == 2
    assert classroom["academic_year"] == 2026
    assert classroom["school_id"] == seeded_users["school"].id


@pytest.mark.asyncio
async def test_teacher_class_summary(
    client,
    seeded_users,
    teacher_analytics_data,
):
    headers = await teacher_headers(client)

    classroom_id = seeded_users["classroom"].id

    response = await client.get(
        f"/teacher/classes/{classroom_id}/summary",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["classroom_id"] == classroom_id
    assert data["classroom_name"] == "Form 2 Test"
    assert data["form_level"] == 2
    assert data["academic_year"] == 2026

    assert data["student_count"] == 1

    assert data["completed_diagnostics"] == 2
    assert data["completed_practice_attempts"] == 2

    assert data["average_diagnostic_score"] == 52.5
    assert data["average_practice_score"] == 75.0


@pytest.mark.asyncio
async def test_teacher_topic_performance(
    client,
    seeded_users,
    teacher_analytics_data,
):
    headers = await teacher_headers(client)

    classroom_id = seeded_users["classroom"].id

    response = await client.get(
        f"/teacher/classes/{classroom_id}/topics",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["classroom_id"] == classroom_id
    assert data["classroom_name"] == "Form 2 Test"

    assert len(data["topics"]) == 3

    topics = {
        topic["topic_slug"]: topic
        for topic in data["topics"]
    }

    transport = topics[
        "transport-in-plants-and-animals"
    ]

    assert transport["students_assessed"] == 1
    assert transport["completed_diagnostics"] == 1
    assert transport["completed_practice_attempts"] == 1
    assert transport["average_diagnostic_score"] == 40.0
    assert transport["average_practice_score"] == 70.0
    assert transport["improvement_percentage_points"] == 30.0

    gaseous_exchange = topics["gaseous-exchange"]

    assert gaseous_exchange["students_assessed"] == 1
    assert gaseous_exchange["completed_diagnostics"] == 1
    assert gaseous_exchange["completed_practice_attempts"] == 1
    assert gaseous_exchange["average_diagnostic_score"] == 65.0
    assert gaseous_exchange["average_practice_score"] == 80.0
    assert gaseous_exchange["improvement_percentage_points"] == 15.0

    respiration = topics["respiration"]

    assert respiration["students_assessed"] == 0
    assert respiration["completed_diagnostics"] == 0
    assert respiration["completed_practice_attempts"] == 0
    assert respiration["average_diagnostic_score"] is None
    assert respiration["average_practice_score"] is None
    assert respiration["improvement_percentage_points"] is None


@pytest.mark.asyncio
async def test_teacher_weak_topic_classification(
    client,
    seeded_users,
    teacher_analytics_data,
):
    headers = await teacher_headers(client)

    classroom_id = seeded_users["classroom"].id

    response = await client.get(
        f"/teacher/classes/{classroom_id}/weak-topics",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["classroom_id"] == classroom_id
    assert data["classroom_name"] == "Form 2 Test"

    assert data["weak_topic_count"] == 2
    assert data["assessed_topic_count"] == 2
    assert data["insufficient_data_topic_count"] == 1

    assert (
        data["weakest_topic_id"]
        == teacher_analytics_data["topic_1"].id
    )

    assert (
        data["weakest_topic_title"]
        == "Transport in Plants and Animals"
    )

    topics = {
        topic["topic_slug"]: topic
        for topic in data["topics"]
    }

    transport = topics[
        "transport-in-plants-and-animals"
    ]

    assert transport["weakness_status"] == "critical"
    assert transport["is_weak"] is True

    gaseous_exchange = topics["gaseous-exchange"]

    assert (
        gaseous_exchange["weakness_status"]
        == "needs_attention"
    )

    assert gaseous_exchange["is_weak"] is True

    respiration = topics["respiration"]

    assert (
        respiration["weakness_status"]
        == "insufficient_data"
    )

    assert respiration["is_weak"] is False


@pytest.mark.asyncio
async def test_teacher_cannot_access_unknown_classroom(
    client,
    seeded_users,
    teacher_analytics_data,
):
    headers = await teacher_headers(client)

    response = await client.get(
        "/teacher/classes/999999/summary",
        headers=headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_student_is_blocked_from_teacher_analytics(
    client,
    seeded_users,
    teacher_analytics_data,
):
    headers = await student_headers(client)

    classroom_id = seeded_users["classroom"].id

    response = await client.get(
        f"/teacher/classes/{classroom_id}/summary",
        headers=headers,
    )

    assert response.status_code == 403
