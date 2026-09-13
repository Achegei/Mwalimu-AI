import pytest
from sqlalchemy import select

from app.models.content import Question, Subject, Topic
from app.models.enums import (
    DifficultyLevel,
    LearningEventType,
    QuestionType,
)
from app.models.learning_event import LearningEvent
from app.models.tutor_message import TutorMessage


class FakeOpenAIResponse:
    def __init__(self, output_text: str):
        self.output_text = output_text


class FakeResponses:
    async def create(
        self,
        model,
        input,
    ):
        if "LATEST STUDENT RESPONSE" in input:
            return FakeOpenAIResponse(
                "Correct. Red blood cells contain haemoglobin, "
                "which carries most of the oxygen in the blood."
            )

        return FakeOpenAIResponse(
            "Red blood cells contain haemoglobin, which binds "
            "and transports most of the oxygen in the blood. "
            "A small amount of oxygen can also dissolve in plasma."
        )


class FakeAsyncOpenAI:
    def __init__(
        self,
        api_key=None,
    ):
        self.responses = FakeResponses()


@pytest.fixture
async def tutor_content(
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

    return {
        "Authorization": (
            f"Bearer {response.json()['access_token']}"
        ),
    }


async def create_completed_diagnostic(
    client,
    headers,
    topic_id,
):
    start_response = await client.post(
        f"/student/topics/{topic_id}/diagnostic/start",
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

    return attempt_id


@pytest.mark.asyncio
async def test_tutor_cannot_start_before_diagnostic_completion(
    client,
    seeded_users,
    tutor_content,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.services.tutor.AsyncOpenAI",
        FakeAsyncOpenAI,
    )

    headers = await student_headers(client)

    topic = tutor_content["topic"]

    start_response = await client.post(
        f"/student/topics/{topic.id}/diagnostic/start",
        headers=headers,
    )

    assert start_response.status_code == 200

    attempt_id = start_response.json()["attempt_id"]

    response = await client.post(
        f"/student/diagnostic/{attempt_id}/tutor/start",
        headers=headers,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_student_can_start_tutor_session(
    client,
    db_session,
    seeded_users,
    tutor_content,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.services.tutor.AsyncOpenAI",
        FakeAsyncOpenAI,
    )

    headers = await student_headers(client)

    topic = tutor_content["topic"]

    attempt_id = await create_completed_diagnostic(
        client=client,
        headers=headers,
        topic_id=topic.id,
    )

    response = await client.post(
        f"/student/diagnostic/{attempt_id}/tutor/start",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["topic_id"] == topic.id
    assert "Red blood cells" in data["message"]
    assert "haemoglobin" in data["message"]

    result = await db_session.execute(
        select(TutorMessage).where(
            TutorMessage.assessment_attempt_id == attempt_id
        )
    )

    messages = list(result.scalars().all())

    assert len(messages) == 1
    assert messages[0].role == "assistant"
    assert "Red blood cells" in messages[0].content

    event_result = await db_session.execute(
        select(LearningEvent).where(
            LearningEvent.assessment_attempt_id == attempt_id,
            LearningEvent.event_type
            == LearningEventType.TUTOR_INTERACTION,
        )
    )

    events = list(event_result.scalars().all())

    assert len(events) == 1
    assert (
        events[0].event_data["interaction_type"]
        == "tutor_started"
    )


@pytest.mark.asyncio
async def test_student_can_continue_tutor_session(
    client,
    db_session,
    seeded_users,
    tutor_content,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.services.tutor.AsyncOpenAI",
        FakeAsyncOpenAI,
    )

    headers = await student_headers(client)

    topic = tutor_content["topic"]

    attempt_id = await create_completed_diagnostic(
        client=client,
        headers=headers,
        topic_id=topic.id,
    )

    start_response = await client.post(
        f"/student/diagnostic/{attempt_id}/tutor/start",
        headers=headers,
    )

    assert start_response.status_code == 200

    reply_response = await client.post(
        f"/student/diagnostic/{attempt_id}/tutor/message",
        headers=headers,
        json={
            "message": (
                "Red blood cells contain haemoglobin "
                "which carries oxygen."
            ),
        },
    )

    assert reply_response.status_code == 200

    data = reply_response.json()

    assert data["topic_id"] == topic.id

    assert (
        data["student_message"]
        == (
            "Red blood cells contain haemoglobin "
            "which carries oxygen."
        )
    )

    assert "Correct" in data["tutor_message"]
    assert "haemoglobin" in data["tutor_message"]

    result = await db_session.execute(
        select(TutorMessage)
        .where(
            TutorMessage.assessment_attempt_id == attempt_id
        )
        .order_by(TutorMessage.id.asc())
    )

    messages = list(result.scalars().all())

    assert len(messages) == 3

    assert messages[0].role == "assistant"
    assert messages[1].role == "student"
    assert messages[2].role == "assistant"

    assert (
        messages[1].content
        == (
            "Red blood cells contain haemoglobin "
            "which carries oxygen."
        )
    )

    assert "Correct" in messages[2].content

    event_result = await db_session.execute(
        select(LearningEvent)
        .where(
            LearningEvent.assessment_attempt_id == attempt_id,
            LearningEvent.event_type
            == LearningEventType.TUTOR_INTERACTION,
        )
        .order_by(LearningEvent.id.asc())
    )

    events = list(event_result.scalars().all())

    assert len(events) == 2

    assert (
        events[0].event_data["interaction_type"]
        == "tutor_started"
    )

    assert (
        events[1].event_data["interaction_type"]
        == "student_reply"
    )


@pytest.mark.asyncio
async def test_empty_tutor_message_is_rejected(
    client,
    seeded_users,
    tutor_content,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.services.tutor.AsyncOpenAI",
        FakeAsyncOpenAI,
    )

    headers = await student_headers(client)

    topic = tutor_content["topic"]

    attempt_id = await create_completed_diagnostic(
        client=client,
        headers=headers,
        topic_id=topic.id,
    )

    response = await client.post(
        f"/student/diagnostic/{attempt_id}/tutor/message",
        headers=headers,
        json={
            "message": "   ",
        },
    )

    assert response.status_code == 400
