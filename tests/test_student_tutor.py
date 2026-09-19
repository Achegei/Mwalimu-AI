import pytest
from sqlalchemy import select

from app.models.content import Question, Subject, Topic
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.enums import (
    DocumentProcessingStatus,
    DocumentType,
    DifficultyLevel,
    LearningEventType,
    QuestionType,
)
from app.models.learning_event import LearningEvent
from app.models.school import School
from app.models.tutor_message import TutorMessage


class FakeOpenAIResponse:
    def __init__(self, output_text: str):
        self.output_text = output_text


class FakeResponses:
    last_input = None

    async def create(
        self,
        model,
        input,
    ):
        FakeResponses.last_input = input

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


@pytest.mark.asyncio
async def test_tutor_prompt_includes_retrieved_school_document_context(
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

    school = seeded_users["school"]
    subject = tutor_content["subject"]
    topic = tutor_content["topic"]

    document = Document(
        school_id=school.id,
        subject_id=subject.id,
        topic_id=topic.id,
        uploaded_by_id=None,
        title="School Biology Reference",
        document_type=DocumentType.TEXTBOOK,
        form_level=topic.form_level,
        academic_year=None,
        exam_year=None,
        paper_number=None,
        original_filename="school-biology-reference.txt",
        storage_key="tests/school-biology-reference.txt",
        mime_type="text/plain",
        file_size=100,
        processing_status=DocumentProcessingStatus.READY,
        error_message=None,
        metadata_json=None,
        is_active=True,
    )

    db_session.add(document)
    await db_session.flush()

    own_school_fact = (
        "SCHOOL DOCUMENT FACT: Red blood cells contain "
        "haemoglobin which transports oxygen around the body."
    )

    db_session.add(
        DocumentChunk(
            document_id=document.id,
            chunk_index=0,
            content=own_school_fact,
            page_number=7,
            character_count=len(own_school_fact),
            metadata_json=None,
        )
    )

    await db_session.commit()

    FakeResponses.last_input = None

    headers = await student_headers(client)

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

    assert FakeResponses.last_input is not None

    prompt = FakeResponses.last_input

    assert "SCHOOL DOCUMENT CONTEXT" in prompt
    assert "School Biology Reference" in prompt
    assert "page 7" in prompt
    assert "SCHOOL DOCUMENT FACT" in prompt
    assert (
        "haemoglobin which transports oxygen"
        in prompt
    )


@pytest.mark.asyncio
async def test_tutor_prompt_excludes_other_school_document_context(
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

    own_school = seeded_users["school"]
    own_subject = tutor_content["subject"]
    own_topic = tutor_content["topic"]

    own_document = Document(
        school_id=own_school.id,
        subject_id=own_subject.id,
        topic_id=own_topic.id,
        uploaded_by_id=None,
        title="Own School Biology Reference",
        document_type=DocumentType.TEXTBOOK,
        form_level=own_topic.form_level,
        academic_year=None,
        exam_year=None,
        paper_number=None,
        original_filename="own-biology.txt",
        storage_key="tests/own-biology.txt",
        mime_type="text/plain",
        file_size=100,
        processing_status=DocumentProcessingStatus.READY,
        error_message=None,
        metadata_json=None,
        is_active=True,
    )

    db_session.add(own_document)
    await db_session.flush()

    own_fact = (
        "OWN SCHOOL FACT: Red blood cells contain "
        "haemoglobin which transports oxygen."
    )

    db_session.add(
        DocumentChunk(
            document_id=own_document.id,
            chunk_index=0,
            content=own_fact,
            page_number=3,
            character_count=len(own_fact),
            metadata_json=None,
        )
    )

    foreign_school = School(
        name="Foreign Tutor School",
        code="TUTOR-FOREIGN-001",
        is_active=True,
    )

    db_session.add(foreign_school)
    await db_session.flush()

    foreign_subject = Subject(
        school_id=foreign_school.id,
        name="Biology",
        slug="biology",
        description="Foreign Biology",
        is_active=True,
    )

    db_session.add(foreign_subject)
    await db_session.flush()

    foreign_topic = Topic(
        subject_id=foreign_subject.id,
        slug="transport-in-plants-and-animals",
        title="Transport in Plants and Animals",
        summary="Foreign curriculum content.",
        form_level=2,
        order_index=1,
        is_active=True,
    )

    db_session.add(foreign_topic)
    await db_session.flush()

    foreign_document = Document(
        school_id=foreign_school.id,
        subject_id=foreign_subject.id,
        topic_id=foreign_topic.id,
        uploaded_by_id=None,
        title="Foreign School Secret Reference",
        document_type=DocumentType.TEXTBOOK,
        form_level=foreign_topic.form_level,
        academic_year=None,
        exam_year=None,
        paper_number=None,
        original_filename="foreign-secret.txt",
        storage_key="tests/foreign-secret.txt",
        mime_type="text/plain",
        file_size=100,
        processing_status=DocumentProcessingStatus.READY,
        error_message=None,
        metadata_json=None,
        is_active=True,
    )

    db_session.add(foreign_document)
    await db_session.flush()

    foreign_fact = (
        "FOREIGN SCHOOL SECRET CONTENT: Red blood cells "
        "contain haemoglobin and transport oxygen."
    )

    db_session.add(
        DocumentChunk(
            document_id=foreign_document.id,
            chunk_index=0,
            content=foreign_fact,
            page_number=99,
            character_count=len(foreign_fact),
            metadata_json=None,
        )
    )

    await db_session.commit()

    FakeResponses.last_input = None

    headers = await student_headers(client)

    attempt_id = await create_completed_diagnostic(
        client=client,
        headers=headers,
        topic_id=own_topic.id,
    )

    response = await client.post(
        f"/student/diagnostic/{attempt_id}/tutor/start",
        headers=headers,
    )

    assert response.status_code == 200
    assert FakeResponses.last_input is not None

    prompt = FakeResponses.last_input

    assert "OWN SCHOOL FACT" in prompt
    assert "Own School Biology Reference" in prompt

    assert "FOREIGN SCHOOL SECRET CONTENT" not in prompt
    assert "Foreign School Secret Reference" not in prompt
    assert "page 99" not in prompt
