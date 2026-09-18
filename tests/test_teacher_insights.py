import pytest

from app.models.assessment import AssessmentAttempt
from app.models.content import Subject, Topic
from app.models.enums import (
    AssessmentStatus,
    AssessmentType,
)
from app.schemas.teacher import (
    TeacherGeneratedInsight,
    TeacherInsightContext,
    TeacherInsightEvidence,
    TeacherInsightTopicContext,
)
from app.services.teacher_insights import (
    generate_teacher_insight,
    validate_teacher_insight,
)


class FakeParsedContent:
    type = "output_text"

    def __init__(self, parsed):
        self.parsed = parsed


class FakeMessageOutput:
    type = "message"

    def __init__(self, parsed):
        self.content = [
            FakeParsedContent(parsed)
        ]


class FakeOpenAIResponse:
    def __init__(self, parsed):
        self.output = [
            FakeMessageOutput(parsed)
        ]


class FakeResponses:
    async def parse(
        self,
        model,
        instructions,
        input,
        text_format,
        temperature,
    ):
        insight = TeacherGeneratedInsight(
            teacher_summary=(
                "Class-level evidence shows that Transport in Plants "
                "and Animals is the weakest assessed topic, classified "
                "as critical. Assessment coverage is limited."
            ),
            main_learning_concern=(
                "Transport in Plants and Animals is classified as "
                "critical based on the available diagnostic evidence."
            ),
            suggested_intervention=(
                "Provide targeted reteaching on Transport in Plants "
                "and Animals, followed by guided practice."
            ),
            follow_up_recommendation=(
                "Reassess the topic after reteaching and collect "
                "additional evidence because current coverage is limited."
            ),
        )

        return FakeOpenAIResponse(insight)


class FakeAsyncOpenAI:
    def __init__(self, api_key=None):
        self.responses = FakeResponses()


@pytest.fixture
async def teacher_insight_data(
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

    db_session.add_all(
        [
            topic_1,
            topic_2,
        ]
    )

    await db_session.flush()

    student = seeded_users["student"]
    classroom = seeded_users["classroom"]

    diagnostic = AssessmentAttempt(
        student_id=student.id,
        classroom_id=classroom.id,
        topic_id=topic_1.id,
        assessment_type=AssessmentType.DIAGNOSTIC,
        status=AssessmentStatus.COMPLETED,
        correct_answers=1,
        total_questions=3,
        score_percentage=40.0,
    )

    practice = AssessmentAttempt(
        student_id=student.id,
        classroom_id=classroom.id,
        topic_id=topic_1.id,
        assessment_type=AssessmentType.PRACTICE,
        status=AssessmentStatus.COMPLETED,
        correct_answers=2,
        total_questions=3,
        score_percentage=70.0,
    )

    db_session.add_all(
        [
            diagnostic,
            practice,
        ]
    )

    await db_session.commit()

    return {
        "subject": subject,
        "topic_1": topic_1,
        "topic_2": topic_2,
        "diagnostic": diagnostic,
        "practice": practice,
    }


def build_valid_context():
    return TeacherInsightContext(
        classroom_id=1,
        classroom_name="Form 2 Test",
        form_level=2,
        academic_year=2026,
        evidence=TeacherInsightEvidence(
            student_count=1,
            assessed_topic_count=1,
            weak_topic_count=1,
            insufficient_data_topic_count=1,
        ),
        weakest_topic=TeacherInsightTopicContext(
            topic_id=1,
            topic_title="Transport in Plants and Animals",
            topic_slug="transport-in-plants-and-animals",
            weakness_status="critical",
            students_assessed=1,
            completed_diagnostics=1,
            completed_practice_attempts=1,
            average_diagnostic_score=40.0,
            average_practice_score=70.0,
            improvement_percentage_points=30.0,
        ),
    )


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
async def test_generate_teacher_insight_with_mocked_openai(
    monkeypatch,
):
    monkeypatch.setattr(
        "app.services.teacher_insights.AsyncOpenAI",
        FakeAsyncOpenAI,
    )

    context = build_valid_context()

    result = await generate_teacher_insight(
        context=context,
    )

    assert isinstance(
        result,
        TeacherGeneratedInsight,
    )

    assert (
        "Transport in Plants and Animals"
        in result.main_learning_concern
    )

    assert "critical" in (
        result.teacher_summary.lower()
        + " "
        + result.main_learning_concern.lower()
    )

    assert "limited" in (
        result.teacher_summary.lower()
        + " "
        + result.follow_up_recommendation.lower()
    )


@pytest.mark.asyncio
async def test_teacher_insight_endpoint(
    client,
    seeded_users,
    teacher_insight_data,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.services.teacher_insights.AsyncOpenAI",
        FakeAsyncOpenAI,
    )

    headers = await teacher_headers(client)

    classroom_id = seeded_users["classroom"].id

    response = await client.get(
        f"/teacher/classes/{classroom_id}/insight",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["context"]["classroom_id"] == classroom_id
    assert (
        data["context"]["classroom_name"]
        == "Form 2 Test"
    )

    evidence = data["context"]["evidence"]

    assert evidence["student_count"] == 1
    assert evidence["assessed_topic_count"] == 1
    assert evidence["weak_topic_count"] == 1
    assert evidence["insufficient_data_topic_count"] == 1

    weakest_topic = data["context"]["weakest_topic"]

    assert weakest_topic is not None
    assert (
        weakest_topic["topic_title"]
        == "Transport in Plants and Animals"
    )
    assert weakest_topic["weakness_status"] == "critical"
    assert weakest_topic["average_diagnostic_score"] == 40.0
    assert weakest_topic["average_practice_score"] == 70.0
    assert (
        weakest_topic["improvement_percentage_points"]
        == 30.0
    )

    insight = data["insight"]

    assert (
        "Transport in Plants and Animals"
        in insight["main_learning_concern"]
    )

    assert "critical" in (
        insight["teacher_summary"].lower()
        + " "
        + insight["main_learning_concern"].lower()
    )


def test_teacher_insight_rejects_individual_student_claim():
    context = build_valid_context()

    insight = TeacherGeneratedInsight(
        teacher_summary=(
            "The student improved after practice."
        ),
        main_learning_concern=(
            "Transport in Plants and Animals is critical."
        ),
        suggested_intervention=(
            "Provide targeted reteaching on "
            "Transport in Plants and Animals."
        ),
        follow_up_recommendation=(
            "Collect more assessment evidence because "
            "coverage is limited."
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="individual-level claim",
    ):
        validate_teacher_insight(
            insight=insight,
            context=context,
        )


def test_teacher_insight_rejects_group_intervention_for_one_student():
    context = build_valid_context()

    insight = TeacherGeneratedInsight(
        teacher_summary=(
            "Transport in Plants and Animals is classified "
            "as critical and evidence coverage is limited."
        ),
        main_learning_concern=(
            "Transport in Plants and Animals is critical."
        ),
        suggested_intervention=(
            "Use small-group instruction for "
            "Transport in Plants and Animals."
        ),
        follow_up_recommendation=(
            "Reassess after instruction because evidence "
            "coverage is limited."
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="group-based",
    ):
        validate_teacher_insight(
            insight=insight,
            context=context,
        )


def test_teacher_insight_requires_weakest_topic_reference():
    context = build_valid_context()

    insight = TeacherGeneratedInsight(
        teacher_summary=(
            "The evidence is limited and the weakest "
            "area is classified as critical."
        ),
        main_learning_concern=(
            "Learners need support with biological concepts."
        ),
        suggested_intervention=(
            "Provide targeted reteaching on the relevant "
            "concept before reassessment."
        ),
        follow_up_recommendation=(
            "Collect additional assessment evidence because "
            "coverage is limited."
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="weakest topic",
    ):
        validate_teacher_insight(
            insight=insight,
            context=context,
        )


def test_teacher_insight_preserves_weakness_classification():
    context = build_valid_context()

    insight = TeacherGeneratedInsight(
        teacher_summary=(
            "Assessment coverage is limited."
        ),
        main_learning_concern=(
            "Transport in Plants and Animals requires review."
        ),
        suggested_intervention=(
            "Provide targeted reteaching on "
            "Transport in Plants and Animals."
        ),
        follow_up_recommendation=(
            "Collect more assessment evidence because "
            "coverage is limited."
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="weakness classification",
    ):
        validate_teacher_insight(
            insight=insight,
            context=context,
        )


def test_teacher_insight_requires_limited_evidence_acknowledgement():
    context = build_valid_context()

    insight = TeacherGeneratedInsight(
        teacher_summary=(
            "Transport in Plants and Animals is critical."
        ),
        main_learning_concern=(
            "Transport in Plants and Animals is classified "
            "as critical."
        ),
        suggested_intervention=(
            "Provide targeted reteaching on "
            "Transport in Plants and Animals."
        ),
        follow_up_recommendation=(
            "Reassess Transport in Plants and Animals "
            "after guided practice."
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="limited assessment coverage",
    ):
        validate_teacher_insight(
            insight=insight,
            context=context,
        )


@pytest.mark.asyncio
async def test_student_is_blocked_from_teacher_insight(
    client,
    seeded_users,
    teacher_insight_data,
):
    headers = await student_headers(client)

    classroom_id = seeded_users["classroom"].id

    response = await client.get(
        f"/teacher/classes/{classroom_id}/insight",
        headers=headers,
    )

    assert response.status_code == 403
