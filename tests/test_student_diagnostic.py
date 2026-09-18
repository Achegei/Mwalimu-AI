import pytest
from sqlalchemy import select

from app.models.assessment import AssessmentAttempt
from app.models.content import Question, Subject, Topic
from app.models.enums import DifficultyLevel, QuestionType


@pytest.fixture
def auth_headers_factory():
    async def make_headers(
        client,
        login_id,
        password,
    ):
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

    return make_headers


@pytest.fixture
async def diagnostic_content(
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


@pytest.mark.asyncio
async def test_student_can_start_diagnostic(
    client,
    seeded_users,
    diagnostic_content,
    auth_headers_factory,
):
    headers = await auth_headers_factory(
        client,
        "student.test",
        "Student123!",
    )

    topic = diagnostic_content["topic"]

    response = await client.post(
        f"/student/topics/{topic.id}/diagnostic/start",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["topic_id"] == topic.id
    assert data["assessment_type"] == "diagnostic"
    assert data["status"] == "in_progress"
    assert len(data["questions"]) == 3


@pytest.mark.asyncio
async def test_diagnostic_scores_answers_deterministically(
    client,
    seeded_users,
    diagnostic_content,
    auth_headers_factory,
):
    headers = await auth_headers_factory(
        client,
        "student.test",
        "Student123!",
    )

    topic = diagnostic_content["topic"]

    start_response = await client.post(
        f"/student/topics/{topic.id}/diagnostic/start",
        headers=headers,
    )

    assert start_response.status_code == 200

    attempt = start_response.json()
    attempt_id = attempt["attempt_id"]

    question = next(
        item
        for item in attempt["questions"]
        if item["prompt"] == "Which tissue transports manufactured food in plants?"
    )

    response = await client.post(
        f"/student/diagnostic/{attempt_id}/answer",
        headers=headers,
        json={
            "question_id": question["id"],
            "answer": "Phloem",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["is_correct"] is True
    assert data["marks_awarded"] == 1


@pytest.mark.asyncio
async def test_diagnostic_rejects_duplicate_answer(
    client,
    seeded_users,
    diagnostic_content,
    auth_headers_factory,
):
    headers = await auth_headers_factory(
        client,
        "student.test",
        "Student123!",
    )

    topic = diagnostic_content["topic"]

    start_response = await client.post(
        f"/student/topics/{topic.id}/diagnostic/start",
        headers=headers,
    )

    attempt = start_response.json()

    attempt_id = attempt["attempt_id"]
    question = attempt["questions"][0]

    first_response = await client.post(
        f"/student/diagnostic/{attempt_id}/answer",
        headers=headers,
        json={
            "question_id": question["id"],
            "answer": "Phloem",
        },
    )

    assert first_response.status_code == 200

    duplicate_response = await client.post(
        f"/student/diagnostic/{attempt_id}/answer",
        headers=headers,
        json={
            "question_id": question["id"],
            "answer": "Phloem",
        },
    )

    assert duplicate_response.status_code == 400


@pytest.mark.asyncio
async def test_diagnostic_cannot_complete_early(
    client,
    seeded_users,
    diagnostic_content,
    auth_headers_factory,
):
    headers = await auth_headers_factory(
        client,
        "student.test",
        "Student123!",
    )

    topic = diagnostic_content["topic"]

    start_response = await client.post(
        f"/student/topics/{topic.id}/diagnostic/start",
        headers=headers,
    )

    attempt = start_response.json()

    attempt_id = attempt["attempt_id"]
    question = attempt["questions"][0]

    answer_response = await client.post(
        f"/student/diagnostic/{attempt_id}/answer",
        headers=headers,
        json={
            "question_id": question["id"],
            "answer": "Phloem",
        },
    )

    assert answer_response.status_code == 200

    complete_response = await client.post(
        f"/student/diagnostic/{attempt_id}/complete",
        headers=headers,
    )

    assert complete_response.status_code == 400


@pytest.mark.asyncio
async def test_student_can_complete_diagnostic(
    client,
    seeded_users,
    diagnostic_content,
    auth_headers_factory,
):
    headers = await auth_headers_factory(
        client,
        "student.test",
        "Student123!",
    )

    topic = diagnostic_content["topic"]

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

    data = complete_response.json()

    assert data["status"] == "completed"
    assert data["correct_answers"] == 2
    assert data["total_questions"] == 3
    assert data["score_percentage"] == 66.67
