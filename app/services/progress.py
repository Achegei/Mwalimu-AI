from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import AssessmentAttempt
from app.models.content import Subject, Topic
from app.models.enums import AssessmentStatus, AssessmentType


async def get_student_progress(
    db: AsyncSession,
    student_id: int,
    school_id: int,
    classroom_id: int | None = None,
) -> dict:
    diagnostic_filters = [
        AssessmentAttempt.student_id == student_id,
        AssessmentAttempt.assessment_type
        == AssessmentType.DIAGNOSTIC,
        AssessmentAttempt.status
        == AssessmentStatus.COMPLETED,
        AssessmentAttempt.score_percentage.is_not(None),
        Subject.school_id == school_id,
    ]

    if classroom_id is not None:
        diagnostic_filters.append(
            AssessmentAttempt.classroom_id == classroom_id,
        )

    diagnostic_result = await db.execute(
        select(
            AssessmentAttempt,
            Topic,
            Subject,
        )
        .join(
            Topic,
            AssessmentAttempt.topic_id == Topic.id,
        )
        .join(
            Subject,
            Topic.subject_id == Subject.id,
        )
        .where(
            *diagnostic_filters,
        )
        .order_by(
            AssessmentAttempt.topic_id,
            AssessmentAttempt.started_at.desc(),
        )
    )

    diagnostic_rows = diagnostic_result.all()

    latest_diagnostics_by_topic: dict[int, tuple] = {}

    for attempt, topic, subject in diagnostic_rows:
        if topic.id not in latest_diagnostics_by_topic:
            latest_diagnostics_by_topic[topic.id] = (
                attempt,
                topic,
                subject,
            )

    topics: list[dict] = []

    improved_topics = 0
    unchanged_topics = 0
    declined_topics = 0

    for diagnostic_attempt, topic, subject in (
        latest_diagnostics_by_topic.values()
    ):
        practice_filters = [
            AssessmentAttempt.student_id == student_id,
            AssessmentAttempt.topic_id == topic.id,
            AssessmentAttempt.assessment_type
            == AssessmentType.PRACTICE,
            AssessmentAttempt.status
            == AssessmentStatus.COMPLETED,
            AssessmentAttempt.score_percentage.is_not(None),
            AssessmentAttempt.started_at
            >= diagnostic_attempt.started_at,
        ]

        if classroom_id is not None:
            practice_filters.append(
                AssessmentAttempt.classroom_id == classroom_id,
            )

        practice_result = await db.execute(
            select(AssessmentAttempt)
            .where(
                *practice_filters,
            )
            .order_by(
                AssessmentAttempt.started_at.desc(),
            )
            .limit(1)
        )

        practice_attempt = practice_result.scalar_one_or_none()

        diagnostic_score = round(
            float(diagnostic_attempt.score_percentage),
            2,
        )

        practice_attempt_id = None
        practice_score = None
        improvement_percentage_points = None
        learning_status = "diagnostic_completed"

        completed_at = diagnostic_attempt.completed_at

        if practice_attempt is not None:
            practice_attempt_id = practice_attempt.id

            practice_score = round(
                float(practice_attempt.score_percentage),
                2,
            )

            improvement_percentage_points = round(
                practice_score - diagnostic_score,
                2,
            )

            if improvement_percentage_points > 0:
                learning_status = "improved"
                improved_topics += 1

            elif improvement_percentage_points == 0:
                learning_status = "unchanged"
                unchanged_topics += 1

            else:
                learning_status = "declined"
                declined_topics += 1

            if practice_attempt.completed_at is not None:
                completed_at = practice_attempt.completed_at

        topics.append(
            {
                "subject_id": subject.id,
                "subject_name": subject.name,
                "topic_id": topic.id,
                "topic_title": topic.title,
                "diagnostic_attempt_id": diagnostic_attempt.id,
                "diagnostic_score": diagnostic_score,
                "practice_attempt_id": practice_attempt_id,
                "practice_score": practice_score,
                "improvement_percentage_points": (
                    improvement_percentage_points
                ),
                "learning_status": learning_status,
                "completed_at": completed_at,
            }
        )

    topics.sort(
        key=lambda item: item["completed_at"],
        reverse=True,
    )

    return {
        "completed_topics": len(topics),
        "improved_topics": improved_topics,
        "unchanged_topics": unchanged_topics,
        "declined_topics": declined_topics,
        "topics": topics,
    }
