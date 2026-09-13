from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import AssessmentAttempt
from app.models.assessment_answer import AssessmentAnswer
from app.models.assessment_question import AssessmentQuestion
from app.models.content import Question, Topic
from app.models.enrollment import Enrollment
from app.models.enums import (
    AssessmentStatus,
    AssessmentType,
    LearningEventType,
)
from app.models.learning_event import LearningEvent


async def get_student_active_classroom_id(
    db: AsyncSession,
    student_id: int,
) -> int:
    enrollment_result = await db.execute(
        select(Enrollment).where(
            Enrollment.student_id == student_id,
            Enrollment.is_active.is_(True),
        )
    )

    enrollments = list(enrollment_result.scalars().all())

    if not enrollments:
        raise ValueError("Student is not enrolled in an active classroom.")

    if len(enrollments) > 1:
        raise ValueError("Student has multiple active classroom enrollments.")

    return enrollments[0].classroom_id


async def start_diagnostic_assessment(
    db: AsyncSession,
    student_id: int,
    topic_id: int,
) -> tuple[AssessmentAttempt, Topic, list[Question]]:
    classroom_id = await get_student_active_classroom_id(
        db=db,
        student_id=student_id,
    )

    topic_result = await db.execute(
        select(Topic).where(
            Topic.id == topic_id,
            Topic.is_active.is_(True),
        )
    )

    topic = topic_result.scalar_one_or_none()

    if topic is None:
        raise ValueError("Topic not found.")

    question_result = await db.execute(
        select(Question)
        .where(
            Question.topic_id == topic.id,
            Question.is_active.is_(True),
        )
        .order_by(Question.id.asc())
        .limit(3)
    )

    questions = list(question_result.scalars().all())

    if not questions:
        raise ValueError("No diagnostic questions are available for this topic.")

    attempt = AssessmentAttempt(
        student_id=student_id,
        classroom_id=classroom_id,
        topic_id=topic.id,
        assessment_type=AssessmentType.DIAGNOSTIC,
        status=AssessmentStatus.IN_PROGRESS,
        correct_answers=0,
        total_questions=len(questions),
        score_percentage=None,
    )

    db.add(attempt)

    # Flush first so attempt.id is available before creating
    # assessment-question assignments and the learning event.
    await db.flush()

    for position, question in enumerate(questions, start=1):
        assessment_question = AssessmentQuestion(
            assessment_attempt_id=attempt.id,
            question_id=question.id,
            position=position,
        )

        db.add(assessment_question)

    diagnostic_started_event = LearningEvent(
        student_id=student_id,
        classroom_id=classroom_id,
        topic_id=topic.id,
        assessment_attempt_id=attempt.id,
        question_id=None,
        event_type=LearningEventType.DIAGNOSTIC_STARTED,
        event_data={
            "assessment_type": AssessmentType.DIAGNOSTIC.value,
            "total_questions": len(questions),
        },
    )

    db.add(diagnostic_started_event)

    await db.commit()
    await db.refresh(attempt)

    return attempt, topic, questions


async def start_practice_assessment(
    db: AsyncSession,
    student_id: int,
    diagnostic_attempt_id: int,
) -> tuple[
    AssessmentAttempt,
    AssessmentAttempt,
    Topic,
    list[Question],
]:
    """
    Start a post-tutoring practice assessment using questions from
    the same topic that were not used in the completed diagnostic.
    """

    diagnostic_result = await db.execute(
        select(AssessmentAttempt).where(
            AssessmentAttempt.id == diagnostic_attempt_id,
            AssessmentAttempt.student_id == student_id,
            AssessmentAttempt.assessment_type == AssessmentType.DIAGNOSTIC,
        )
    )

    diagnostic_attempt = diagnostic_result.scalar_one_or_none()

    if diagnostic_attempt is None:
        raise ValueError("Diagnostic attempt not found.")

    if diagnostic_attempt.status != AssessmentStatus.COMPLETED:
        raise ValueError(
            "Diagnostic attempt must be completed before starting practice."
        )

    topic_result = await db.execute(
        select(Topic).where(
            Topic.id == diagnostic_attempt.topic_id,
            Topic.is_active.is_(True),
        )
    )

    topic = topic_result.scalar_one_or_none()

    if topic is None:
        raise ValueError("Topic not found.")

    diagnostic_answers_result = await db.execute(
        select(AssessmentAnswer.question_id).where(
            AssessmentAnswer.assessment_attempt_id == diagnostic_attempt.id
        )
    )

    diagnostic_question_ids = list(diagnostic_answers_result.scalars().all())

    if not diagnostic_question_ids:
        raise ValueError("Diagnostic attempt has no recorded answers.")

    practice_questions_result = await db.execute(
        select(Question)
        .where(
            Question.topic_id == diagnostic_attempt.topic_id,
            Question.is_active.is_(True),
            Question.id.not_in(diagnostic_question_ids),
        )
        .order_by(Question.id.asc())
        .limit(3)
    )

    practice_questions = list(practice_questions_result.scalars().all())

    if len(practice_questions) < 3:
        raise ValueError(
            "Not enough unused practice questions are available for this topic."
        )

    classroom_id = diagnostic_attempt.classroom_id

    if classroom_id is None:
        classroom_id = await get_student_active_classroom_id(
            db=db,
            student_id=student_id,
        )

    practice_attempt = AssessmentAttempt(
        student_id=student_id,
        classroom_id=classroom_id,
        topic_id=diagnostic_attempt.topic_id,
        assessment_type=AssessmentType.PRACTICE,
        status=AssessmentStatus.IN_PROGRESS,
        correct_answers=0,
        total_questions=len(practice_questions),
        score_percentage=None,
    )

    db.add(practice_attempt)

    # Flush so practice_attempt.id is available for
    # question assignments and the learning event.
    await db.flush()

    for position, question in enumerate(
        practice_questions,
        start=1,
    ):
        assessment_question = AssessmentQuestion(
            assessment_attempt_id=practice_attempt.id,
            question_id=question.id,
            position=position,
        )

        db.add(assessment_question)

    practice_started_event = LearningEvent(
        student_id=student_id,
        classroom_id=classroom_id,
        topic_id=diagnostic_attempt.topic_id,
        assessment_attempt_id=practice_attempt.id,
        question_id=None,
        event_type=LearningEventType.PRACTICE_STARTED,
        event_data={
            "assessment_type": AssessmentType.PRACTICE.value,
            "diagnostic_attempt_id": diagnostic_attempt.id,
            "total_questions": len(practice_questions),
            "excluded_diagnostic_question_ids": (diagnostic_question_ids),
        },
    )

    db.add(practice_started_event)

    await db.commit()
    await db.refresh(practice_attempt)

    return (
        practice_attempt,
        diagnostic_attempt,
        topic,
        practice_questions,
    )


async def submit_diagnostic_answer(
    db: AsyncSession,
    student_id: int,
    attempt_id: int,
    question_id: int,
    submitted_answer: str,
) -> tuple[AssessmentAnswer, Question]:
    attempt_result = await db.execute(
        select(AssessmentAttempt).where(
            AssessmentAttempt.id == attempt_id,
            AssessmentAttempt.student_id == student_id,
            AssessmentAttempt.assessment_type == AssessmentType.DIAGNOSTIC,
        )
    )

    attempt = attempt_result.scalar_one_or_none()

    if attempt is None:
        raise ValueError("Diagnostic assessment attempt not found.")

    if attempt.status != AssessmentStatus.IN_PROGRESS:
        raise ValueError("Assessment attempt is no longer in progress.")

    assignment_result = await db.execute(
        select(AssessmentQuestion).where(
            AssessmentQuestion.assessment_attempt_id == attempt.id,
            AssessmentQuestion.question_id == question_id,
        )
    )

    assignment = assignment_result.scalar_one_or_none()

    if assignment is None:
        raise ValueError("Question was not assigned to this assessment attempt.")

    question_result = await db.execute(
        select(Question).where(
            Question.id == question_id,
            Question.topic_id == attempt.topic_id,
            Question.is_active.is_(True),
        )
    )

    question = question_result.scalar_one_or_none()

    if question is None:
        raise ValueError("Assessment question not found.")

    existing_result = await db.execute(
        select(AssessmentAnswer).where(
            AssessmentAnswer.assessment_attempt_id == attempt.id,
            AssessmentAnswer.question_id == question.id,
        )
    )

    existing_answer = existing_result.scalar_one_or_none()

    if existing_answer is not None:
        raise ValueError("This question has already been answered.")

    normalized_submitted_answer = submitted_answer.strip().casefold()
    normalized_correct_answer = question.correct_answer.strip().casefold()

    is_correct = normalized_submitted_answer == normalized_correct_answer

    marks_awarded = question.marks if is_correct else 0

    answer = AssessmentAnswer(
        assessment_attempt_id=attempt.id,
        question_id=question.id,
        submitted_answer=submitted_answer.strip(),
        is_correct=is_correct,
        marks_awarded=marks_awarded,
    )

    db.add(answer)

    question_answered_event = LearningEvent(
        student_id=student_id,
        classroom_id=attempt.classroom_id,
        topic_id=attempt.topic_id,
        assessment_attempt_id=attempt.id,
        question_id=question.id,
        event_type=LearningEventType.QUESTION_ANSWERED,
        event_data={
            "assessment_type": AssessmentType.DIAGNOSTIC.value,
            "is_correct": is_correct,
            "marks_awarded": marks_awarded,
            "question_type": question.question_type.value,
            "difficulty": question.difficulty.value,
        },
    )

    db.add(question_answered_event)

    await db.commit()
    await db.refresh(answer)

    return answer, question


async def submit_practice_answer(
    db: AsyncSession,
    student_id: int,
    attempt_id: int,
    question_id: int,
    submitted_answer: str,
) -> tuple[AssessmentAnswer, Question]:
    attempt_result = await db.execute(
        select(AssessmentAttempt).where(
            AssessmentAttempt.id == attempt_id,
            AssessmentAttempt.student_id == student_id,
            AssessmentAttempt.assessment_type == AssessmentType.PRACTICE,
        )
    )

    attempt = attempt_result.scalar_one_or_none()

    if attempt is None:
        raise ValueError("Practice assessment attempt not found.")

    if attempt.status != AssessmentStatus.IN_PROGRESS:
        raise ValueError("Assessment attempt is no longer in progress.")

    assignment_result = await db.execute(
        select(AssessmentQuestion).where(
            AssessmentQuestion.assessment_attempt_id == attempt.id,
            AssessmentQuestion.question_id == question_id,
        )
    )

    assignment = assignment_result.scalar_one_or_none()

    if assignment is None:
        raise ValueError("Question was not assigned to this assessment attempt.")

    question_result = await db.execute(
        select(Question).where(
            Question.id == question_id,
            Question.topic_id == attempt.topic_id,
            Question.is_active.is_(True),
        )
    )

    question = question_result.scalar_one_or_none()

    if question is None:
        raise ValueError("Assessment question not found.")

    existing_result = await db.execute(
        select(AssessmentAnswer).where(
            AssessmentAnswer.assessment_attempt_id == attempt.id,
            AssessmentAnswer.question_id == question.id,
        )
    )

    existing_answer = existing_result.scalar_one_or_none()

    if existing_answer is not None:
        raise ValueError("This question has already been answered.")

    normalized_submitted_answer = submitted_answer.strip().casefold()
    normalized_correct_answer = question.correct_answer.strip().casefold()

    is_correct = normalized_submitted_answer == normalized_correct_answer

    marks_awarded = question.marks if is_correct else 0

    answer = AssessmentAnswer(
        assessment_attempt_id=attempt.id,
        question_id=question.id,
        submitted_answer=submitted_answer.strip(),
        is_correct=is_correct,
        marks_awarded=marks_awarded,
    )

    db.add(answer)

    question_answered_event = LearningEvent(
        student_id=student_id,
        classroom_id=attempt.classroom_id,
        topic_id=attempt.topic_id,
        assessment_attempt_id=attempt.id,
        question_id=question.id,
        event_type=LearningEventType.QUESTION_ANSWERED,
        event_data={
            "assessment_type": AssessmentType.PRACTICE.value,
            "is_correct": is_correct,
            "marks_awarded": marks_awarded,
            "question_type": question.question_type.value,
            "difficulty": question.difficulty.value,
        },
    )

    db.add(question_answered_event)

    await db.commit()
    await db.refresh(answer)

    return answer, question


async def complete_diagnostic_assessment(
    db: AsyncSession,
    student_id: int,
    attempt_id: int,
) -> AssessmentAttempt:
    attempt_result = await db.execute(
        select(AssessmentAttempt).where(
            AssessmentAttempt.id == attempt_id,
            AssessmentAttempt.student_id == student_id,
            AssessmentAttempt.assessment_type == AssessmentType.DIAGNOSTIC,
        )
    )

    attempt = attempt_result.scalar_one_or_none()

    if attempt is None:
        raise ValueError("Assessment attempt not found.")

    if attempt.status != AssessmentStatus.IN_PROGRESS:
        raise ValueError("Assessment attempt is no longer in progress.")

    answers_result = await db.execute(
        select(AssessmentAnswer).where(
            AssessmentAnswer.assessment_attempt_id == attempt.id
        )
    )

    answers = list(answers_result.scalars().all())

    if len(answers) < attempt.total_questions:
        remaining = attempt.total_questions - len(answers)

        raise ValueError(
            f"Assessment is incomplete. {remaining} question(s) remaining."
        )

    correct_answers = sum(1 for answer in answers if answer.is_correct)

    score_percentage = round(
        (correct_answers / attempt.total_questions) * 100,
        2,
    )

    attempt.correct_answers = correct_answers
    attempt.score_percentage = score_percentage
    attempt.status = AssessmentStatus.COMPLETED
    attempt.completed_at = datetime.now(timezone.utc)

    assessment_completed_event = LearningEvent(
        student_id=student_id,
        classroom_id=attempt.classroom_id,
        topic_id=attempt.topic_id,
        assessment_attempt_id=attempt.id,
        question_id=None,
        event_type=LearningEventType.ASSESSMENT_COMPLETED,
        event_data={
            "assessment_type": AssessmentType.DIAGNOSTIC.value,
            "correct_answers": correct_answers,
            "total_questions": attempt.total_questions,
            "score_percentage": score_percentage,
        },
    )

    db.add(assessment_completed_event)

    await db.commit()
    await db.refresh(attempt)

    return attempt


async def complete_practice_assessment(
    db: AsyncSession,
    student_id: int,
    attempt_id: int,
) -> AssessmentAttempt:
    attempt_result = await db.execute(
        select(AssessmentAttempt).where(
            AssessmentAttempt.id == attempt_id,
            AssessmentAttempt.student_id == student_id,
            AssessmentAttempt.assessment_type == AssessmentType.PRACTICE,
        )
    )

    attempt = attempt_result.scalar_one_or_none()

    if attempt is None:
        raise ValueError("Practice assessment attempt not found.")

    if attempt.status != AssessmentStatus.IN_PROGRESS:
        raise ValueError("Assessment attempt is no longer in progress.")

    answers_result = await db.execute(
        select(AssessmentAnswer).where(
            AssessmentAnswer.assessment_attempt_id == attempt.id
        )
    )

    answers = list(answers_result.scalars().all())

    if len(answers) < attempt.total_questions:
        remaining = attempt.total_questions - len(answers)

        raise ValueError(
            f"Assessment is incomplete. {remaining} question(s) remaining."
        )

    correct_answers = sum(1 for answer in answers if answer.is_correct)

    score_percentage = round(
        (correct_answers / attempt.total_questions) * 100,
        2,
    )

    attempt.correct_answers = correct_answers
    attempt.score_percentage = score_percentage
    attempt.status = AssessmentStatus.COMPLETED
    attempt.completed_at = datetime.now(timezone.utc)

    practice_completed_event = LearningEvent(
        student_id=student_id,
        classroom_id=attempt.classroom_id,
        topic_id=attempt.topic_id,
        assessment_attempt_id=attempt.id,
        question_id=None,
        event_type=LearningEventType.PRACTICE_COMPLETED,
        event_data={
            "assessment_type": AssessmentType.PRACTICE.value,
            "correct_answers": correct_answers,
            "total_questions": attempt.total_questions,
            "score_percentage": score_percentage,
        },
    )

    assessment_completed_event = LearningEvent(
        student_id=student_id,
        classroom_id=attempt.classroom_id,
        topic_id=attempt.topic_id,
        assessment_attempt_id=attempt.id,
        question_id=None,
        event_type=LearningEventType.ASSESSMENT_COMPLETED,
        event_data={
            "assessment_type": AssessmentType.PRACTICE.value,
            "correct_answers": correct_answers,
            "total_questions": attempt.total_questions,
            "score_percentage": score_percentage,
        },
    )

    db.add(practice_completed_event)
    db.add(assessment_completed_event)

    await db.commit()
    await db.refresh(attempt)

    return attempt


async def compare_diagnostic_to_practice(
    db: AsyncSession,
    student_id: int,
    diagnostic_attempt_id: int,
) -> dict:
    """
    Compare a completed diagnostic assessment with the student's
    completed practice assessment for the same topic.

    Returns deterministic learning-improvement data.
    """

    diagnostic_result = await db.execute(
        select(AssessmentAttempt).where(
            AssessmentAttempt.id == diagnostic_attempt_id,
            AssessmentAttempt.student_id == student_id,
            AssessmentAttempt.assessment_type == AssessmentType.DIAGNOSTIC,
            AssessmentAttempt.status == AssessmentStatus.COMPLETED,
        )
    )

    diagnostic_attempt = diagnostic_result.scalar_one_or_none()

    if diagnostic_attempt is None:
        raise ValueError("Completed diagnostic assessment attempt not found.")

    practice_result = await db.execute(
        select(AssessmentAttempt)
        .where(
            AssessmentAttempt.student_id == student_id,
            AssessmentAttempt.topic_id == diagnostic_attempt.topic_id,
            AssessmentAttempt.assessment_type == AssessmentType.PRACTICE,
            AssessmentAttempt.status == AssessmentStatus.COMPLETED,
            AssessmentAttempt.started_at >= diagnostic_attempt.started_at,
        )
        .order_by(AssessmentAttempt.started_at.desc())
        .limit(1)
    )

    practice_attempt = practice_result.scalar_one_or_none()

    if practice_attempt is None:
        raise ValueError("Completed practice assessment not found for this diagnostic.")

    if diagnostic_attempt.score_percentage is None:
        raise ValueError("Diagnostic assessment does not have a score.")

    if practice_attempt.score_percentage is None:
        raise ValueError("Practice assessment does not have a score.")

    diagnostic_score = round(
        float(diagnostic_attempt.score_percentage),
        2,
    )

    practice_score = round(
        float(practice_attempt.score_percentage),
        2,
    )

    improvement_percentage_points = round(
        practice_score - diagnostic_score,
        2,
    )

    improved = improvement_percentage_points > 0

    if improvement_percentage_points > 0:
        learning_status = "improved"
    elif improvement_percentage_points == 0:
        learning_status = "unchanged"
    else:
        learning_status = "declined"

    return {
        "diagnostic_attempt_id": diagnostic_attempt.id,
        "practice_attempt_id": practice_attempt.id,
        "topic_id": diagnostic_attempt.topic_id,
        "diagnostic_score": diagnostic_score,
        "practice_score": practice_score,
        "improvement_percentage_points": (improvement_percentage_points),
        "improved": improved,
        "learning_status": learning_status,
    }


async def build_learning_improvement_result(
    db: AsyncSession,
    student_id: int,
    diagnostic_attempt_id: int,
) -> dict:
    comparison = await compare_diagnostic_to_practice(
        db=db,
        student_id=student_id,
        diagnostic_attempt_id=diagnostic_attempt_id,
    )

    diagnostic_score = comparison["diagnostic_score"]
    practice_score = comparison["practice_score"]
    improvement = comparison["improvement_percentage_points"]
    learning_status = comparison["learning_status"]

    if learning_status == "improved":
        message = (
            f"Your score improved from {diagnostic_score}% "
            f"to {practice_score}%, an improvement of "
            f"{improvement} percentage points."
        )
        recommended_action = (
            "Continue to the next topic or complete another practice "
            "session later to reinforce your understanding."
        )

    elif learning_status == "unchanged":
        message = f"Your score remained at {practice_score}% after practice."
        recommended_action = "Review the topic again with the tutor and retry practice."

    else:
        decline = abs(improvement)

        message = (
            f"Your score changed from {diagnostic_score}% "
            f"to {practice_score}%, a decrease of "
            f"{decline} percentage points."
        )
        recommended_action = (
            "Review the weak concepts with the tutor before attempting "
            "another practice session."
        )

    return {
        **comparison,
        "message": message,
        "recommended_action": recommended_action,
    }
