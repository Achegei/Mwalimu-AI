from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import AssessmentAttempt
from app.models.assessment_answer import AssessmentAnswer
from app.models.content import Question
from app.models.enums import AssessmentStatus, AssessmentType
from app.services.content import get_active_topic_for_school


def get_performance_level(score_percentage: float) -> str:
    if score_percentage >= 80:
        return "strong"

    if score_percentage >= 60:
        return "developing"

    return "needs_support"


def build_recommended_action(
    weak_questions: list[Question],
) -> str:
    if not weak_questions:
        return (
            "Continue to the next learning activity and reinforce "
            "the topic through practice."
        )

    difficulties = [question.difficulty.value for question in weak_questions]

    most_common_difficulty = Counter(difficulties).most_common(1)[0][0]

    return (
        f"Review the concepts linked to the incorrectly answered "
        f"{most_common_difficulty} question(s) before continuing."
    )


async def interpret_diagnostic_attempt(
    db: AsyncSession,
    student_id: int,
    school_id: int,
    attempt_id: int,
) -> dict:
    attempt_result = await db.execute(
        select(AssessmentAttempt).where(
            AssessmentAttempt.id == attempt_id,
            AssessmentAttempt.student_id == student_id,
            AssessmentAttempt.assessment_type == AssessmentType.DIAGNOSTIC,
        )
    )

    attempt = attempt_result.scalar_one_or_none()

    if attempt is None:
        raise ValueError("Diagnostic attempt not found.")

    if attempt.status != AssessmentStatus.COMPLETED:
        raise ValueError("Diagnostic attempt must be completed before interpretation.")

    topic = await get_active_topic_for_school(
        db=db,
        topic_id=attempt.topic_id,
        school_id=school_id,
    )

    if topic is None:
        raise ValueError("Topic not found.")

    answer_result = await db.execute(
        select(
            AssessmentAnswer,
            Question,
        )
        .join(
            Question,
            AssessmentAnswer.question_id == Question.id,
        )
        .where(AssessmentAnswer.assessment_attempt_id == attempt.id)
        .order_by(Question.id.asc())
    )

    rows = answer_result.all()

    weak_questions = [question for answer, question in rows if not answer.is_correct]

    weak_question_ids = [question.id for question in weak_questions]

    weak_difficulties = sorted(
        {question.difficulty.value for question in weak_questions}
    )

    score_percentage = float(attempt.score_percentage or 0)

    performance_level = get_performance_level(score_percentage)

    recommended_action = build_recommended_action(weak_questions)

    return {
        "attempt_id": attempt.id,
        "topic_id": attempt.topic_id,
        "score_percentage": score_percentage,
        "performance_level": performance_level,
        "weak_questions": weak_question_ids,
        "weak_difficulties": weak_difficulties,
        "recommended_action": recommended_action,
    }
