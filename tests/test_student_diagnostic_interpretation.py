import pytest
from sqlalchemy import select

from app.models.assessment import AssessmentAttempt
from app.models.content import Question, Subject, Topic
from app.models.enums import DifficultyLevel, QuestionType


@pytest.fixture
async def interpretation_content(
    db_session,
    seeded_users,
):
    subject = Subject(
        school_id=seeded_users["school"].id,
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
            options=[
                "Xylem",
                "Phloem",
                "Cambium",
                "Epidermis",
            ],
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
            options=[
                "True",
                "False",
            ],
            correct_answer="True",
            explanation="Arteries carry blood away from the heart.",
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


async def student_headers(
    client,
):
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


@pytest.mark.asyncio
async def test_completed_diagnostic_has_classroom_id(
    client,
    db_session,
    seeded_users,
    interpretation_content,
):
    headers = await student_headers(client)

    topic = interpretation_content["topic"]

    start_response = await client.post(
        f"/student/topics/{topic.id}/diagnostic/start",
        headers=headers,
    )

    assert start_response.status_code == 200

    attempt = start_response.json()
    attempt_id = attempt["attempt_id"]

    answer_map = {
        "Which tissue transports manufactured food in plants?": "Phloem",
        "Which blood cells mainly transport oxygen?": "Plasma",
        "Arteries carry blood away from the heart.": "True",
    }

    for question in attempt["questions"]:
        response = await client.post(
            f"/student/diagnostic/{attempt_id}/answer",
            headers=headers,
            json={
                "question_id": question["id"],
                "answer": answer_map[question["prompt"]],
            },
        )

        assert response.status_code == 200

    complete_response = await client.post(
        f"/student/diagnostic/{attempt_id}/complete",
        headers=headers,
    )

    assert complete_response.status_code == 200

    result = await db_session.execute(
        select(AssessmentAttempt).where(AssessmentAttempt.id == attempt_id)
    )

    assessment_attempt = result.scalar_one()

    assert assessment_attempt.classroom_id == seeded_users["classroom"].id


@pytest.mark.asyncio
async def test_diagnostic_interpretation_identifies_weakness(
    client,
    seeded_users,
    interpretation_content,
):
    headers = await student_headers(client)

    topic = interpretation_content["topic"]

    start_response = await client.post(
        f"/student/topics/{topic.id}/diagnostic/start",
        headers=headers,
    )

    assert start_response.status_code == 200

    attempt = start_response.json()
    attempt_id = attempt["attempt_id"]

    question_by_prompt = {
        question["prompt"]: question for question in attempt["questions"]
    }

    answer_map = {
        "Which tissue transports manufactured food in plants?": "Phloem",
        "Which blood cells mainly transport oxygen?": "Plasma",
        "Arteries carry blood away from the heart.": "True",
    }

    for question in attempt["questions"]:
        response = await client.post(
            f"/student/diagnostic/{attempt_id}/answer",
            headers=headers,
            json={
                "question_id": question["id"],
                "answer": answer_map[question["prompt"]],
            },
        )

        assert response.status_code == 200

    complete_response = await client.post(
        f"/student/diagnostic/{attempt_id}/complete",
        headers=headers,
    )

    assert complete_response.status_code == 200

    interpretation_response = await client.get(
        f"/student/diagnostic/{attempt_id}/interpretation",
        headers=headers,
    )

    assert interpretation_response.status_code == 200

    data = interpretation_response.json()

    wrong_question_id = question_by_prompt[
        "Which blood cells mainly transport oxygen?"
    ]["id"]

    assert data["attempt_id"] == attempt_id
    assert data["topic_id"] == topic.id
    assert data["score_percentage"] == 66.67
    assert data["performance_level"] == "developing"
    assert data["weak_questions"] == [wrong_question_id]
    assert data["weak_difficulties"] == ["medium"]

    assert data["recommended_action"] == (
        "Review the concepts linked to the incorrectly "
        "answered medium question(s) before continuing."
    )


@pytest.mark.asyncio
async def test_interpretation_rejects_incomplete_diagnostic(
    client,
    seeded_users,
    interpretation_content,
):
    headers = await student_headers(client)

    topic = interpretation_content["topic"]

    start_response = await client.post(
        f"/student/topics/{topic.id}/diagnostic/start",
        headers=headers,
    )

    assert start_response.status_code == 200

    attempt_id = start_response.json()["attempt_id"]

    response = await client.get(
        f"/student/diagnostic/{attempt_id}/interpretation",
        headers=headers,
    )

    assert response.status_code == 400
