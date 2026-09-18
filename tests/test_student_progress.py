from datetime import datetime, timedelta, timezone

import pytest

from app.models.assessment import AssessmentAttempt
from app.models.content import Subject, Topic
from app.models.enums import AssessmentStatus, AssessmentType


async def login_student(client) -> dict[str, str]:
    response = await client.post(
        "/auth/login",
        json={
            "login_id": "student.test",
            "password": "Student123!",
        },
    )

    assert response.status_code == 200

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }


async def login_teacher(client) -> dict[str, str]:
    response = await client.post(
        "/auth/login",
        json={
            "login_id": "teacher.test",
            "password": "Teacher123!",
        },
    )

    assert response.status_code == 200

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }


async def create_subject_and_topic(
    db_session,
    *,
    school_id: int,
    topic_slug: str = "gaseous-exchange",
    topic_title: str = "Gaseous Exchange",
):
    subject = Subject(
        school_id=school_id,
        name="Biology",
        slug="biology",
        description="Form 2 Biology",
        is_active=True,
    )

    db_session.add(subject)
    await db_session.flush()

    topic = Topic(
        subject_id=subject.id,
        slug=topic_slug,
        title=topic_title,
        summary="Test topic.",
        form_level=2,
        order_index=1,
        is_active=True,
    )

    db_session.add(topic)
    await db_session.flush()

    return subject, topic


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_access_student_progress(
    client,
):
    response = await client.get(
        "/student/progress",
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_teacher_cannot_access_student_progress(
    client,
    seeded_users,
):
    headers = await login_teacher(client)

    response = await client.get(
        "/student/progress",
        headers=headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_student_progress_empty_state(
    client,
    seeded_users,
):
    headers = await login_student(client)

    response = await client.get(
        "/student/progress",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data == {
        "completed_topics": 0,
        "improved_topics": 0,
        "unchanged_topics": 0,
        "declined_topics": 0,
        "topics": [],
    }


@pytest.mark.asyncio
async def test_student_progress_shows_completed_diagnostic_without_practice(
    client,
    db_session,
    seeded_users,
):
    _, topic = await create_subject_and_topic(
        db_session,
        school_id=seeded_users["school"].id,
    )

    student = seeded_users["student"]
    classroom = seeded_users["classroom"]

    completed_at = datetime(
        2026,
        9,
        13,
        9,
        0,
        tzinfo=timezone.utc,
    )

    diagnostic = AssessmentAttempt(
        student_id=student.id,
        topic_id=topic.id,
        classroom_id=classroom.id,
        assessment_type=AssessmentType.DIAGNOSTIC,
        status=AssessmentStatus.COMPLETED,
        correct_answers=1,
        total_questions=3,
        score_percentage=33.33,
        started_at=completed_at - timedelta(minutes=5),
        completed_at=completed_at,
    )

    db_session.add(diagnostic)
    await db_session.commit()

    headers = await login_student(client)

    response = await client.get(
        "/student/progress",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["completed_topics"] == 1
    assert data["improved_topics"] == 0
    assert data["unchanged_topics"] == 0
    assert data["declined_topics"] == 0

    assert len(data["topics"]) == 1

    progress = data["topics"][0]

    assert progress["subject_name"] == "Biology"
    assert progress["topic_title"] == "Gaseous Exchange"
    assert progress["diagnostic_attempt_id"] == diagnostic.id
    assert progress["diagnostic_score"] == 33.33

    assert progress["practice_attempt_id"] is None
    assert progress["practice_score"] is None
    assert progress["improvement_percentage_points"] is None
    assert progress["learning_status"] == "diagnostic_completed"


@pytest.mark.asyncio
async def test_student_progress_calculates_improvement_from_practice(
    client,
    db_session,
    seeded_users,
):
    _, topic = await create_subject_and_topic(
        db_session,
        school_id=seeded_users["school"].id,
    )

    student = seeded_users["student"]
    classroom = seeded_users["classroom"]

    diagnostic_started_at = datetime(
        2026,
        9,
        13,
        9,
        0,
        tzinfo=timezone.utc,
    )

    diagnostic = AssessmentAttempt(
        student_id=student.id,
        topic_id=topic.id,
        classroom_id=classroom.id,
        assessment_type=AssessmentType.DIAGNOSTIC,
        status=AssessmentStatus.COMPLETED,
        correct_answers=1,
        total_questions=3,
        score_percentage=33.33,
        started_at=diagnostic_started_at,
        completed_at=diagnostic_started_at + timedelta(minutes=5),
    )

    db_session.add(diagnostic)
    await db_session.flush()

    practice_started_at = diagnostic_started_at + timedelta(minutes=20)

    practice = AssessmentAttempt(
        student_id=student.id,
        topic_id=topic.id,
        classroom_id=classroom.id,
        assessment_type=AssessmentType.PRACTICE,
        status=AssessmentStatus.COMPLETED,
        correct_answers=3,
        total_questions=3,
        score_percentage=100.0,
        started_at=practice_started_at,
        completed_at=practice_started_at + timedelta(minutes=5),
    )

    db_session.add(practice)
    await db_session.commit()

    headers = await login_student(client)

    response = await client.get(
        "/student/progress",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["completed_topics"] == 1
    assert data["improved_topics"] == 1
    assert data["unchanged_topics"] == 0
    assert data["declined_topics"] == 0

    progress = data["topics"][0]

    assert progress["diagnostic_attempt_id"] == diagnostic.id
    assert progress["practice_attempt_id"] == practice.id
    assert progress["diagnostic_score"] == 33.33
    assert progress["practice_score"] == 100.0
    assert progress["improvement_percentage_points"] == 66.67
    assert progress["learning_status"] == "improved"


@pytest.mark.asyncio
async def test_student_progress_uses_latest_completed_diagnostic_per_topic(
    client,
    db_session,
    seeded_users,
):
    _, topic = await create_subject_and_topic(
        db_session,
        school_id=seeded_users["school"].id,
    )

    student = seeded_users["student"]
    classroom = seeded_users["classroom"]

    base_time = datetime(
        2026,
        9,
        13,
        8,
        0,
        tzinfo=timezone.utc,
    )

    old_diagnostic = AssessmentAttempt(
        student_id=student.id,
        topic_id=topic.id,
        classroom_id=classroom.id,
        assessment_type=AssessmentType.DIAGNOSTIC,
        status=AssessmentStatus.COMPLETED,
        correct_answers=1,
        total_questions=3,
        score_percentage=33.33,
        started_at=base_time,
        completed_at=base_time + timedelta(minutes=5),
    )

    db_session.add(old_diagnostic)
    await db_session.flush()

    old_practice = AssessmentAttempt(
        student_id=student.id,
        topic_id=topic.id,
        classroom_id=classroom.id,
        assessment_type=AssessmentType.PRACTICE,
        status=AssessmentStatus.COMPLETED,
        correct_answers=3,
        total_questions=3,
        score_percentage=100.0,
        started_at=base_time + timedelta(minutes=20),
        completed_at=base_time + timedelta(minutes=25),
    )

    db_session.add(old_practice)
    await db_session.flush()

    latest_diagnostic_started_at = base_time + timedelta(hours=2)

    latest_diagnostic = AssessmentAttempt(
        student_id=student.id,
        topic_id=topic.id,
        classroom_id=classroom.id,
        assessment_type=AssessmentType.DIAGNOSTIC,
        status=AssessmentStatus.COMPLETED,
        correct_answers=2,
        total_questions=3,
        score_percentage=66.67,
        started_at=latest_diagnostic_started_at,
        completed_at=(
            latest_diagnostic_started_at
            + timedelta(minutes=5)
        ),
    )

    db_session.add(latest_diagnostic)
    await db_session.commit()

    headers = await login_student(client)

    response = await client.get(
        "/student/progress",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["completed_topics"] == 1

    progress = data["topics"][0]

    assert progress["diagnostic_attempt_id"] == latest_diagnostic.id
    assert progress["diagnostic_score"] == 66.67

    assert progress["practice_attempt_id"] is None
    assert progress["practice_score"] is None
    assert progress["improvement_percentage_points"] is None
    assert progress["learning_status"] == "diagnostic_completed"
