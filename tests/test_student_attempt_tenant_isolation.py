from datetime import datetime, timedelta, timezone

import pytest

from app.models.assessment import AssessmentAttempt
from app.models.assessment_answer import AssessmentAnswer
from app.models.content import Question, Subject, Topic
from app.models.enums import (
    AssessmentStatus,
    AssessmentType,
    DifficultyLevel,
    QuestionType,
)
from app.models.school import School


class FakeOpenAIResponse:
    def __init__(self, output_text: str):
        self.output_text = output_text


class FakeResponses:
    async def create(
        self,
        model,
        input,
    ):
        return FakeOpenAIResponse(
            "This response should never be generated for "
            "another school's curriculum."
        )


class FakeAsyncOpenAI:
    def __init__(
        self,
        api_key=None,
    ):
        self.responses = FakeResponses()


async def login_student(
    client,
) -> dict[str, str]:
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


@pytest.fixture
async def forged_foreign_attempts(
    db_session,
    seeded_users,
):
    """
    Create malformed historical assessment records where the local
    student owns the attempts, but the topic belongs to another school.

    The data is deliberately complete enough for tutor, practice,
    interpretation, improvement, and progress logic to otherwise work.
    """

    foreign_school = School(
        name="Foreign Secondary School",
        code="FOREIGN-ATTEMPT-001",
        is_active=True,
    )

    db_session.add(foreign_school)
    await db_session.flush()

    foreign_subject = Subject(
        school_id=foreign_school.id,
        name="Biology",
        slug="biology",
        description="Biology owned by another school.",
        is_active=True,
    )

    db_session.add(foreign_subject)
    await db_session.flush()

    foreign_topic = Topic(
        subject_id=foreign_subject.id,
        slug="foreign-transport",
        title="Foreign Transport Topic",
        summary="Private curriculum content from another school.",
        form_level=2,
        order_index=1,
        is_active=True,
    )

    db_session.add(foreign_topic)
    await db_session.flush()

    questions = []

    for index in range(1, 7):
        question = Question(
            topic_id=foreign_topic.id,
            question_type=QuestionType.MULTIPLE_CHOICE,
            difficulty=(
                DifficultyLevel.EASY
                if index <= 3
                else DifficultyLevel.MEDIUM
            ),
            prompt=f"Foreign curriculum question {index}?",
            options=[
                "Answer A",
                "Answer B",
                "Answer C",
                "Answer D",
            ],
            correct_answer="Answer A",
            explanation=(
                f"Foreign curriculum explanation {index}."
            ),
            marks=1,
            is_active=True,
        )

        questions.append(question)

    db_session.add_all(questions)
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
        topic_id=foreign_topic.id,
        assessment_type=AssessmentType.DIAGNOSTIC,
        status=AssessmentStatus.COMPLETED,
        correct_answers=2,
        total_questions=3,
        score_percentage=66.67,
        started_at=diagnostic_started_at,
        completed_at=diagnostic_started_at + timedelta(minutes=5),
    )

    db_session.add(diagnostic)
    await db_session.flush()

    diagnostic_answers = [
        AssessmentAnswer(
            assessment_attempt_id=diagnostic.id,
            question_id=questions[0].id,
            submitted_answer="Answer A",
            is_correct=True,
            marks_awarded=1,
        ),
        AssessmentAnswer(
            assessment_attempt_id=diagnostic.id,
            question_id=questions[1].id,
            submitted_answer="Answer B",
            is_correct=False,
            marks_awarded=0,
        ),
        AssessmentAnswer(
            assessment_attempt_id=diagnostic.id,
            question_id=questions[2].id,
            submitted_answer="Answer A",
            is_correct=True,
            marks_awarded=1,
        ),
    ]

    db_session.add_all(diagnostic_answers)
    await db_session.flush()

    practice_started_at = diagnostic_started_at + timedelta(minutes=20)

    practice = AssessmentAttempt(
        student_id=student.id,
        classroom_id=classroom.id,
        topic_id=foreign_topic.id,
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

    return {
        "school": foreign_school,
        "subject": foreign_subject,
        "topic": foreign_topic,
        "questions": questions,
        "diagnostic": diagnostic,
        "practice": practice,
    }


@pytest.mark.asyncio
async def test_student_cannot_start_tutor_for_foreign_school_attempt(
    client,
    seeded_users,
    forged_foreign_attempts,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.services.tutor.AsyncOpenAI",
        FakeAsyncOpenAI,
    )

    headers = await login_student(client)

    diagnostic = forged_foreign_attempts["diagnostic"]

    response = await client.post(
        f"/student/diagnostic/{diagnostic.id}/tutor/start",
        headers=headers,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_student_cannot_start_practice_for_foreign_school_attempt(
    client,
    seeded_users,
    forged_foreign_attempts,
):
    headers = await login_student(client)

    diagnostic = forged_foreign_attempts["diagnostic"]

    response = await client.post(
        f"/student/diagnostic/{diagnostic.id}/practice/start",
        headers=headers,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_student_cannot_interpret_foreign_school_attempt(
    client,
    seeded_users,
    forged_foreign_attempts,
):
    headers = await login_student(client)

    diagnostic = forged_foreign_attempts["diagnostic"]

    response = await client.get(
        (
            f"/student/diagnostic/"
            f"{diagnostic.id}/interpretation"
        ),
        headers=headers,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_student_cannot_get_improvement_for_foreign_school_attempt(
    client,
    seeded_users,
    forged_foreign_attempts,
):
    headers = await login_student(client)

    diagnostic = forged_foreign_attempts["diagnostic"]

    response = await client.get(
        (
            f"/student/diagnostic/"
            f"{diagnostic.id}/improvement"
        ),
        headers=headers,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_student_progress_excludes_foreign_school_attempts(
    client,
    seeded_users,
    forged_foreign_attempts,
):
    headers = await login_student(client)

    response = await client.get(
        "/student/progress",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    foreign_subject = forged_foreign_attempts["subject"]
    foreign_topic = forged_foreign_attempts["topic"]

    subject_ids = {
        item["subject_id"]
        for item in data["topics"]
    }

    topic_ids = {
        item["topic_id"]
        for item in data["topics"]
    }

    assert foreign_subject.id not in subject_ids
    assert foreign_topic.id not in topic_ids
