from datetime import datetime, timedelta, timezone

import pytest

from app.core.security import hash_password
from app.models.assessment import AssessmentAttempt
from app.models.classroom import Classroom
from app.models.content import Subject, Topic
from app.models.enrollment import Enrollment
from app.models.enums import (
    AssessmentStatus,
    AssessmentType,
    UserRole,
)
from app.models.teaching_assignment import TeachingAssignment
from app.models.user import User


async def login_teacher(client) -> dict[str, str]:
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


async def login_student(client) -> dict[str, str]:
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
async def test_unauthenticated_user_cannot_list_class_students(
    client,
    seeded_users,
):
    classroom_id = seeded_users["classroom"].id

    response = await client.get(
        f"/teacher/classes/{classroom_id}/students",
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_student_role_cannot_list_class_students(
    client,
    seeded_users,
):
    headers = await login_student(client)

    classroom_id = seeded_users["classroom"].id

    response = await client.get(
        f"/teacher/classes/{classroom_id}/students",
        headers=headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_teacher_can_list_students_in_own_class(
    client,
    seeded_users,
):
    headers = await login_teacher(client)

    classroom_id = seeded_users["classroom"].id
    student = seeded_users["student"]

    response = await client.get(
        f"/teacher/classes/{classroom_id}/students",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1

    assert data[0] == {
        "student_id": student.id,
        "full_name": student.full_name,
        "login_id": student.login_id,
    }


@pytest.mark.asyncio
async def test_teacher_can_view_enrolled_student_progress(
    client,
    db_session,
    seeded_users,
):
    subject = Subject(
        school_id=seeded_users["school"].id,
        name="Biology",
        slug="biology-teacher-progress",
        description="Teacher progress test.",
        is_active=True,
    )

    db_session.add(subject)
    await db_session.flush()

    topic = Topic(
        subject_id=subject.id,
        slug="teacher-progress-topic",
        title="Teacher Progress Topic",
        summary="Teacher progress test topic.",
        form_level=2,
        order_index=1,
        is_active=True,
    )

    db_session.add(topic)
    await db_session.flush()

    student = seeded_users["student"]
    classroom = seeded_users["classroom"]

    diagnostic_started_at = datetime(
        2026,
        9,
        13,
        10,
        0,
        tzinfo=timezone.utc,
    )

    diagnostic = AssessmentAttempt(
        student_id=student.id,
        classroom_id=classroom.id,
        topic_id=topic.id,
        assessment_type=AssessmentType.DIAGNOSTIC,
        status=AssessmentStatus.COMPLETED,
        correct_answers=1,
        total_questions=3,
        score_percentage=33.33,
        started_at=diagnostic_started_at,
        completed_at=(
            diagnostic_started_at
            + timedelta(minutes=5)
        ),
    )

    db_session.add(diagnostic)
    await db_session.flush()

    practice_started_at = (
        diagnostic_started_at
        + timedelta(minutes=20)
    )

    practice = AssessmentAttempt(
        student_id=student.id,
        classroom_id=classroom.id,
        topic_id=topic.id,
        assessment_type=AssessmentType.PRACTICE,
        status=AssessmentStatus.COMPLETED,
        correct_answers=3,
        total_questions=3,
        score_percentage=100.0,
        started_at=practice_started_at,
        completed_at=(
            practice_started_at
            + timedelta(minutes=5)
        ),
    )

    db_session.add(practice)
    await db_session.commit()

    headers = await login_teacher(client)

    response = await client.get(
        (
            f"/teacher/classes/{classroom.id}"
            f"/students/{student.id}/progress"
        ),
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["classroom_id"] == classroom.id
    assert data["classroom_name"] == classroom.name

    assert data["student"] == {
        "student_id": student.id,
        "full_name": student.full_name,
        "login_id": student.login_id,
    }

    progress = data["progress"]

    assert progress["completed_topics"] == 1
    assert progress["improved_topics"] == 1
    assert progress["unchanged_topics"] == 0
    assert progress["declined_topics"] == 0

    assert len(progress["topics"]) == 1

    topic_progress = progress["topics"][0]

    assert topic_progress["subject_name"] == "Biology"
    assert (
        topic_progress["topic_title"]
        == "Teacher Progress Topic"
    )
    assert topic_progress["diagnostic_score"] == 33.33
    assert topic_progress["practice_score"] == 100.0
    assert (
        topic_progress["improvement_percentage_points"]
        == 66.67
    )
    assert topic_progress["learning_status"] == "improved"


@pytest.mark.asyncio
async def test_teacher_cannot_access_unknown_classroom_students(
    client,
    seeded_users,
):
    headers = await login_teacher(client)

    response = await client.get(
        "/teacher/classes/999999/students",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Classroom not found."


@pytest.mark.asyncio
async def test_teacher_cannot_access_unenrolled_student_progress(
    client,
    db_session,
    seeded_users,
):
    school = seeded_users["school"]
    classroom = seeded_users["classroom"]

    unenrolled_student = User(
        school_id=school.id,
        login_id="unenrolled.student",
        full_name="Unenrolled Student",
        role=UserRole.STUDENT,
        password_hash=hash_password("Student123!"),
        is_active=True,
    )

    db_session.add(unenrolled_student)
    await db_session.commit()

    headers = await login_teacher(client)

    response = await client.get(
        (
            f"/teacher/classes/{classroom.id}"
            f"/students/{unenrolled_student.id}/progress"
        ),
        headers=headers,
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Student not found in this classroom."
    )


@pytest.mark.asyncio
async def test_teacher_cannot_access_student_through_another_classroom(
    client,
    db_session,
    seeded_users,
):
    school = seeded_users["school"]
    teacher = seeded_users["teacher"]
    student = seeded_users["student"]

    other_classroom = Classroom(
        school_id=school.id,
        name="Other Form 2 Class",
        form_level=2,
        academic_year=2026,
    )

    db_session.add(other_classroom)
    await db_session.flush()

    teaching_assignment = TeachingAssignment(
        school_id=school.id,
        teacher_id=teacher.id,
        subject_id=seeded_users["subject"].id,
        classroom_id=other_classroom.id,
        is_active=True,
    )

    db_session.add(teaching_assignment)
    await db_session.flush()

    headers = await login_teacher(client)

    response = await client.get(
        (
            f"/teacher/classes/{other_classroom.id}"
            f"/students/{student.id}/progress"
        ),
        headers=headers,
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Student not found in this classroom."
    )


@pytest.mark.asyncio
async def test_inactive_enrollment_does_not_grant_progress_access(
    client,
    db_session,
    seeded_users,
):
    classroom = seeded_users["classroom"]
    student = seeded_users["student"]

    result = await db_session.get(
        Enrollment,
        seeded_users["enrollment"].id,
    )

    result.is_active = False

    await db_session.commit()

    headers = await login_teacher(client)

    response = await client.get(
        (
            f"/teacher/classes/{classroom.id}"
            f"/students/{student.id}/progress"
        ),
        headers=headers,
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Student not found in this classroom."
    )


@pytest.mark.asyncio
async def test_teacher_student_progress_is_scoped_to_requested_classroom(
    client,
    db_session,
    seeded_users,
):
    school = seeded_users["school"]
    teacher = seeded_users["teacher"]
    student = seeded_users["student"]
    classroom = seeded_users["classroom"]

    subject = Subject(
        school_id=seeded_users["school"].id,
        name="Biology",
        slug="biology-classroom-scope",
        description="Classroom scoping test.",
        is_active=True,
    )

    db_session.add(subject)
    await db_session.flush()

    topic = Topic(
        subject_id=subject.id,
        slug="classroom-scope-topic",
        title="Classroom Scope Topic",
        summary="Tests classroom-scoped progress.",
        form_level=2,
        order_index=1,
        is_active=True,
    )

    db_session.add(topic)
    await db_session.flush()

    other_classroom = Classroom(
        school_id=school.id,
        name="Second Form 2 Class",
        form_level=2,
        academic_year=2026,
    )

    db_session.add(other_classroom)
    await db_session.flush()

    other_enrollment = Enrollment(
        classroom_id=other_classroom.id,
        student_id=student.id,
        is_active=True,
    )

    db_session.add(other_enrollment)
    await db_session.flush()

    base_time = datetime(
        2026,
        9,
        13,
        8,
        0,
        tzinfo=timezone.utc,
    )

    original_diagnostic = AssessmentAttempt(
        student_id=student.id,
        classroom_id=classroom.id,
        topic_id=topic.id,
        assessment_type=AssessmentType.DIAGNOSTIC,
        status=AssessmentStatus.COMPLETED,
        correct_answers=1,
        total_questions=3,
        score_percentage=40.0,
        started_at=base_time,
        completed_at=base_time + timedelta(minutes=5),
    )

    original_practice = AssessmentAttempt(
        student_id=student.id,
        classroom_id=classroom.id,
        topic_id=topic.id,
        assessment_type=AssessmentType.PRACTICE,
        status=AssessmentStatus.COMPLETED,
        correct_answers=2,
        total_questions=3,
        score_percentage=70.0,
        started_at=base_time + timedelta(minutes=20),
        completed_at=base_time + timedelta(minutes=25),
    )

    other_diagnostic = AssessmentAttempt(
        student_id=student.id,
        classroom_id=other_classroom.id,
        topic_id=topic.id,
        assessment_type=AssessmentType.DIAGNOSTIC,
        status=AssessmentStatus.COMPLETED,
        correct_answers=3,
        total_questions=3,
        score_percentage=100.0,
        started_at=base_time + timedelta(hours=2),
        completed_at=(
            base_time
            + timedelta(hours=2, minutes=5)
        ),
    )

    other_practice = AssessmentAttempt(
        student_id=student.id,
        classroom_id=other_classroom.id,
        topic_id=topic.id,
        assessment_type=AssessmentType.PRACTICE,
        status=AssessmentStatus.COMPLETED,
        correct_answers=3,
        total_questions=3,
        score_percentage=100.0,
        started_at=(
            base_time
            + timedelta(hours=2, minutes=20)
        ),
        completed_at=(
            base_time
            + timedelta(hours=2, minutes=25)
        ),
    )

    db_session.add_all(
        [
            original_diagnostic,
            original_practice,
            other_diagnostic,
            other_practice,
        ]
    )

    await db_session.commit()

    headers = await login_teacher(client)

    response = await client.get(
        (
            f"/teacher/classes/{classroom.id}"
            f"/students/{student.id}/progress"
        ),
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["classroom_id"] == classroom.id

    progress = data["progress"]

    assert progress["completed_topics"] == 1
    assert len(progress["topics"]) == 1

    topic_progress = progress["topics"][0]

    assert topic_progress["topic_title"] == "Classroom Scope Topic"

    assert (
        topic_progress["diagnostic_attempt_id"]
        == original_diagnostic.id
    )

    assert (
        topic_progress["practice_attempt_id"]
        == original_practice.id
    )

    assert topic_progress["diagnostic_score"] == 40.0
    assert topic_progress["practice_score"] == 70.0
    assert (
        topic_progress["improvement_percentage_points"]
        == 30.0
    )
    assert topic_progress["learning_status"] == "improved"

    assert (
        topic_progress["diagnostic_attempt_id"]
        != other_diagnostic.id
    )

    assert (
        topic_progress["practice_attempt_id"]
        != other_practice.id
    )
