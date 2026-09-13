import pytest
from sqlalchemy import select

from app.models.assessment import AssessmentAttempt
from app.models.assessment_question import AssessmentQuestion
from app.models.content import Question, Subject, Topic
from app.models.enums import (
    DifficultyLevel,
    LearningEventType,
    QuestionType,
)
from app.models.learning_event import LearningEvent


@pytest.fixture
async def practice_content(
    db_session,
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
    await db_session.flush()

    questions = [
        Question(
            topic_id=topic.id,
            question_type=QuestionType.MULTIPLE_CHOICE,
            difficulty=DifficultyLevel.EASY,
            prompt="Which tissue transports manufactured food in plants?",
            options=["Xylem", "Phloem", "Cambium", "Epidermis"],
            correct_answer="Phloem",
            explanation="Phloem transports manufactured food.",
            marks=1,
            is_active=True,
        ),
        Question(
            topic_id=topic.id,
            question_type=QuestionType.MULTIPLE_CHOICE,
            difficulty=DifficultyLevel.MEDIUM,
            prompt="Which blood cells mainly transport oxygen?",
            options=[
                "Red blood cells",
                "White blood cells",
                "Platelets",
                "Plasma",
            ],
            correct_answer="Red blood cells",
            explanation="Red blood cells contain haemoglobin.",
            marks=1,
            is_active=True,
        ),
        Question(
            topic_id=topic.id,
            question_type=QuestionType.TRUE_FALSE,
            difficulty=DifficultyLevel.MEDIUM,
            prompt="Arteries carry blood away from the heart.",
            options=["True", "False"],
            correct_answer="True",
            explanation="Arteries carry blood away from the heart.",
            marks=1,
            is_active=True,
        ),
        Question(
            topic_id=topic.id,
            question_type=QuestionType.MULTIPLE_CHOICE,
            difficulty=DifficultyLevel.EASY,
            prompt="Which blood vessels carry blood away from the heart?",
            options=[
                "Arteries",
                "Veins",
                "Capillaries",
                "Venules",
            ],
            correct_answer="Arteries",
            explanation="Arteries carry blood away from the heart.",
            marks=1,
            is_active=True,
        ),
        Question(
            topic_id=topic.id,
            question_type=QuestionType.MULTIPLE_CHOICE,
            difficulty=DifficultyLevel.MEDIUM,
            prompt=(
                "Which feature of red blood cells helps them "
                "transport oxygen?"
            ),
            options=[
                "They contain haemoglobin",
                "They contain chlorophyll",
                "They produce antibodies",
                "They digest bacteria",
            ],
            correct_answer="They contain haemoglobin",
            explanation=(
                "Haemoglobin binds oxygen for transport."
            ),
            marks=1,
            is_active=True,
        ),
        Question(
            topic_id=topic.id,
            question_type=QuestionType.TRUE_FALSE,
            difficulty=DifficultyLevel.MEDIUM,
            prompt=(
                "Capillaries have thin walls that allow "
                "exchange of substances."
            ),
            options=["True", "False"],
            correct_answer="True",
            explanation=(
                "Thin capillary walls allow efficient exchange."
            ),
            marks=1,
            is_active=True,
        ),
    ]

    db_session.add_all(questions)
    await db_session.commit()

    return {
        "subject": subject,
        "topic": topic,
        "questions": questions,
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


async def start_diagnostic(
    client,
    headers,
    topic_id,
):
    response = await client.post(
        f"/student/topics/{topic_id}/diagnostic/start",
        headers=headers,
    )

    assert response.status_code == 200

    return response.json()


async def complete_diagnostic(
    client,
    headers,
    topic_id,
):
    diagnostic = await start_diagnostic(
        client=client,
        headers=headers,
        topic_id=topic_id,
    )

    answer_map = {
        "Which tissue transports manufactured food in plants?": (
            "Phloem"
        ),
        "Which blood cells mainly transport oxygen?": (
            "Plasma"
        ),
        "Arteries carry blood away from the heart.": (
            "True"
        ),
    }

    for question in diagnostic["questions"]:
        response = await client.post(
            (
                f"/student/diagnostic/"
                f"{diagnostic['attempt_id']}/answer"
            ),
            headers=headers,
            json={
                "question_id": question["id"],
                "answer": answer_map[question["prompt"]],
            },
        )

        assert response.status_code == 200

    response = await client.post(
        (
            f"/student/diagnostic/"
            f"{diagnostic['attempt_id']}/complete"
        ),
        headers=headers,
    )

    assert response.status_code == 200

    return diagnostic


async def start_completed_diagnostic_and_practice(
    client,
    headers,
    topic_id,
):
    diagnostic = await complete_diagnostic(
        client=client,
        headers=headers,
        topic_id=topic_id,
    )

    response = await client.post(
        (
            f"/student/diagnostic/"
            f"{diagnostic['attempt_id']}/practice/start"
        ),
        headers=headers,
    )

    assert response.status_code == 200

    return diagnostic, response.json()


@pytest.mark.asyncio
async def test_practice_requires_completed_diagnostic(
    client,
    seeded_users,
    practice_content,
):
    headers = await student_headers(client)

    diagnostic = await start_diagnostic(
        client=client,
        headers=headers,
        topic_id=practice_content["topic"].id,
    )

    response = await client.post(
        (
            f"/student/diagnostic/"
            f"{diagnostic['attempt_id']}/practice/start"
        ),
        headers=headers,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_practice_uses_three_new_questions_and_classroom(
    client,
    db_session,
    seeded_users,
    practice_content,
):
    headers = await student_headers(client)

    diagnostic, practice = (
        await start_completed_diagnostic_and_practice(
            client=client,
            headers=headers,
            topic_id=practice_content["topic"].id,
        )
    )

    assert practice["diagnostic_attempt_id"] == diagnostic["attempt_id"]
    assert practice["topic_id"] == practice_content["topic"].id
    assert practice["assessment_type"] == "practice"
    assert practice["status"] == "in_progress"
    assert practice["total_questions"] == 3
    assert len(practice["questions"]) == 3

    diagnostic_question_ids = {
        question["id"]
        for question in diagnostic["questions"]
    }

    practice_question_ids = {
        question["id"]
        for question in practice["questions"]
    }

    assert diagnostic_question_ids.isdisjoint(
        practice_question_ids
    )

    result = await db_session.execute(
        select(AssessmentAttempt).where(
            AssessmentAttempt.id == practice["attempt_id"]
        )
    )

    attempt = result.scalar_one()

    assert (
        attempt.classroom_id
        == seeded_users["classroom"].id
    )

    assignment_result = await db_session.execute(
        select(AssessmentQuestion).where(
            AssessmentQuestion.assessment_attempt_id
            == practice["attempt_id"]
        )
    )

    assignments = list(
        assignment_result.scalars().all()
    )

    assert len(assignments) == 3

    assigned_ids = {
        assignment.question_id
        for assignment in assignments
    }

    assert assigned_ids == practice_question_ids


@pytest.mark.asyncio
async def test_practice_scoring_and_duplicate_protection(
    client,
    seeded_users,
    practice_content,
):
    headers = await student_headers(client)

    _, practice = await start_completed_diagnostic_and_practice(
        client=client,
        headers=headers,
        topic_id=practice_content["topic"].id,
    )

    question = practice["questions"][0]

    response = await client.post(
        f"/student/practice/{practice['attempt_id']}/answer",
        headers=headers,
        json={
            "question_id": question["id"],
            "submitted_answer": "Arteries",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["is_correct"] is True
    assert data["marks_awarded"] == 1

    duplicate_response = await client.post(
        f"/student/practice/{practice['attempt_id']}/answer",
        headers=headers,
        json={
            "question_id": question["id"],
            "submitted_answer": "Arteries",
        },
    )

    assert duplicate_response.status_code == 400


@pytest.mark.asyncio
async def test_practice_rejects_unassigned_question(
    client,
    seeded_users,
    practice_content,
):
    headers = await student_headers(client)

    diagnostic, practice = (
        await start_completed_diagnostic_and_practice(
            client=client,
            headers=headers,
            topic_id=practice_content["topic"].id,
        )
    )

    diagnostic_question_id = diagnostic["questions"][0]["id"]

    response = await client.post(
        f"/student/practice/{practice['attempt_id']}/answer",
        headers=headers,
        json={
            "question_id": diagnostic_question_id,
            "submitted_answer": "Phloem",
        },
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_practice_cannot_complete_until_all_questions_answered(
    client,
    seeded_users,
    practice_content,
):
    headers = await student_headers(client)

    _, practice = await start_completed_diagnostic_and_practice(
        client=client,
        headers=headers,
        topic_id=practice_content["topic"].id,
    )

    response = await client.post(
        f"/student/practice/{practice['attempt_id']}/complete",
        headers=headers,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_practice_completion_and_learning_improvement(
    client,
    db_session,
    seeded_users,
    practice_content,
):
    headers = await student_headers(client)

    diagnostic, practice = (
        await start_completed_diagnostic_and_practice(
            client=client,
            headers=headers,
            topic_id=practice_content["topic"].id,
        )
    )

    correct_answers = {
        (
            "Which blood vessels carry blood away "
            "from the heart?"
        ): "Arteries",
        (
            "Which feature of red blood cells helps them "
            "transport oxygen?"
        ): "They contain haemoglobin",
        (
            "Capillaries have thin walls that allow "
            "exchange of substances."
        ): "True",
    }

    for question in practice["questions"]:
        response = await client.post(
            (
                f"/student/practice/"
                f"{practice['attempt_id']}/answer"
            ),
            headers=headers,
            json={
                "question_id": question["id"],
                "submitted_answer": (
                    correct_answers[question["prompt"]]
                ),
            },
        )

        assert response.status_code == 200
        assert response.json()["is_correct"] is True

    completion_response = await client.post(
        f"/student/practice/{practice['attempt_id']}/complete",
        headers=headers,
    )

    assert completion_response.status_code == 200

    completion = completion_response.json()

    assert completion["assessment_type"] == "practice"
    assert completion["status"] == "completed"
    assert completion["correct_answers"] == 3
    assert completion["total_questions"] == 3
    assert completion["score_percentage"] == 100.0

    improvement_response = await client.get(
        (
            f"/student/diagnostic/"
            f"{diagnostic['attempt_id']}/improvement"
        ),
        headers=headers,
    )

    assert improvement_response.status_code == 200

    improvement = improvement_response.json()

    assert (
        improvement["diagnostic_attempt_id"]
        == diagnostic["attempt_id"]
    )

    assert (
        improvement["practice_attempt_id"]
        == practice["attempt_id"]
    )

    assert improvement["topic_id"] == practice_content["topic"].id
    assert improvement["diagnostic_score"] == 66.67
    assert improvement["practice_score"] == 100.0
    assert improvement["improvement_percentage_points"] == 33.33
    assert improvement["improved"] is True
    assert improvement["learning_status"] == "improved"

    event_result = await db_session.execute(
        select(LearningEvent)
        .where(
            LearningEvent.assessment_attempt_id
            == practice["attempt_id"]
        )
        .order_by(LearningEvent.id.asc())
    )

    events = list(event_result.scalars().all())

    event_types = [
        event.event_type
        for event in events
    ]

    assert LearningEventType.PRACTICE_STARTED in event_types
    assert LearningEventType.PRACTICE_COMPLETED in event_types
    assert LearningEventType.ASSESSMENT_COMPLETED in event_types

    question_answered_events = [
        event
        for event in events
        if event.event_type
        == LearningEventType.QUESTION_ANSWERED
    ]

    assert len(question_answered_events) == 3

    for event in question_answered_events:
        assert (
            event.event_data["assessment_type"]
            == "practice"
        )
        assert event.event_data["is_correct"] is True
