import pytest

from app.models.content import Question, Subject, Topic
from app.models.enums import DifficultyLevel, QuestionType
from app.models.school import School


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


@pytest.fixture
async def foreign_school_content(
    db_session,
):
    """
    Create active curriculum content belonging to a second school.

    The authenticated test student belongs to TEST-001.
    Everything in this fixture belongs to TEST-002.
    """

    foreign_school = School(
        name="Foreign Secondary School",
        code="TEST-002",
        is_active=True,
    )

    db_session.add(foreign_school)
    await db_session.flush()

    foreign_subject = Subject(
        school_id=foreign_school.id,
        name="Biology",
        slug="biology",
        description="Biology content owned by another school.",
        is_active=True,
    )

    db_session.add(foreign_subject)
    await db_session.flush()

    foreign_topic = Topic(
        subject_id=foreign_subject.id,
        slug="foreign-gaseous-exchange",
        title="Foreign Gaseous Exchange",
        summary="Curriculum content belonging to another school.",
        form_level=2,
        order_index=1,
        is_active=True,
    )

    db_session.add(foreign_topic)
    await db_session.flush()

    questions = [
        Question(
            topic_id=foreign_topic.id,
            question_type=QuestionType.MULTIPLE_CHOICE,
            difficulty=DifficultyLevel.EASY,
            prompt="Foreign school question one?",
            options=[
                "Answer A",
                "Answer B",
                "Answer C",
                "Answer D",
            ],
            correct_answer="Answer A",
            explanation="Foreign school explanation one.",
            marks=1,
            is_active=True,
        ),
        Question(
            topic_id=foreign_topic.id,
            question_type=QuestionType.MULTIPLE_CHOICE,
            difficulty=DifficultyLevel.MEDIUM,
            prompt="Foreign school question two?",
            options=[
                "Answer A",
                "Answer B",
                "Answer C",
                "Answer D",
            ],
            correct_answer="Answer B",
            explanation="Foreign school explanation two.",
            marks=1,
            is_active=True,
        ),
        Question(
            topic_id=foreign_topic.id,
            question_type=QuestionType.TRUE_FALSE,
            difficulty=DifficultyLevel.MEDIUM,
            prompt="Foreign school question three?",
            options=[
                "True",
                "False",
            ],
            correct_answer="True",
            explanation="Foreign school explanation three.",
            marks=1,
            is_active=True,
        ),
    ]

    db_session.add_all(questions)
    await db_session.commit()

    return {
        "school": foreign_school,
        "subject": foreign_subject,
        "topic": foreign_topic,
        "questions": questions,
    }


@pytest.mark.asyncio
async def test_student_subject_list_excludes_other_school_subjects(
    client,
    seeded_users,
    foreign_school_content,
):
    headers = await login_student(client)

    response = await client.get(
        "/student/subjects",
        headers=headers,
    )

    assert response.status_code == 200

    subjects = response.json()

    foreign_subject = foreign_school_content["subject"]

    subject_ids = {
        subject["id"]
        for subject in subjects
    }

    assert foreign_subject.id not in subject_ids

    for subject in subjects:
        assert subject["id"] != foreign_subject.id


@pytest.mark.asyncio
async def test_student_cannot_list_topics_for_other_school_subject(
    client,
    seeded_users,
    foreign_school_content,
):
    headers = await login_student(client)

    foreign_subject = foreign_school_content["subject"]

    response = await client.get(
        f"/student/subjects/{foreign_subject.id}/topics",
        headers=headers,
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Subject not found.",
    }


@pytest.mark.asyncio
async def test_student_cannot_start_diagnostic_for_other_school_topic(
    client,
    seeded_users,
    foreign_school_content,
):
    headers = await login_student(client)

    foreign_topic = foreign_school_content["topic"]

    response = await client.post(
        f"/student/topics/{foreign_topic.id}/diagnostic/start",
        headers=headers,
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Topic not found.",
    }
