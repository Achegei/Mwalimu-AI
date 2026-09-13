from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.content import (
    DiagnosticAnswerRequest,
    DiagnosticAnswerResponse,
    DiagnosticInterpretationResponse,
    DiagnosticResultResponse,
    DiagnosticStartResponse,
    LearningImprovementResponse,
    PracticeAnswerRequest,
    PracticeAnswerResponse,
    PracticeCompleteResponse,
    PracticeStartResponse,
    SubjectSummary,
    SubjectWithTopics,
    StudentProgressResponse,
    TutorMessageRequest,
    TutorMessageResponse,
    TutorStartResponse,
)
from app.services.assessment import (
    build_learning_improvement_result,
    complete_diagnostic_assessment,
    complete_practice_assessment,
    start_diagnostic_assessment,
    start_practice_assessment,
    submit_diagnostic_answer,
    submit_practice_answer,
)
from app.services.content import (
    get_active_subjects,
    get_active_topics_for_subject,
)
from app.services.diagnostic import interpret_diagnostic_attempt
from app.services.progress import get_student_progress
from app.services.tutor import (
    continue_tutor_session,
    start_tutor_session,
)

router = APIRouter(
    prefix="/student",
    tags=["Student"],
)


@router.get(
    "/progress",
    response_model=StudentProgressResponse,
)
async def student_progress(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
) -> StudentProgressResponse:
    progress = await get_student_progress(
        db=db,
        student_id=current_user.id,
    )

    return StudentProgressResponse(**progress)


@router.get(
    "/subjects",
    response_model=list[SubjectSummary],
)
async def list_subjects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
) -> list[SubjectSummary]:
    subjects = await get_active_subjects(db)

    return subjects


@router.get(
    "/subjects/{subject_id}/topics",
    response_model=SubjectWithTopics,
)
async def list_subject_topics(
    subject_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
) -> SubjectWithTopics:
    subjects = await get_active_subjects(db)

    subject = next(
        (item for item in subjects if item.id == subject_id),
        None,
    )

    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found.",
        )

    topics = await get_active_topics_for_subject(
        db=db,
        subject_id=subject.id,
        form_level=2,
    )

    return SubjectWithTopics(
        id=subject.id,
        name=subject.name,
        slug=subject.slug,
        description=subject.description,
        topics=topics,
    )


@router.post(
    "/topics/{topic_id}/diagnostic/start",
    response_model=DiagnosticStartResponse,
)
async def start_diagnostic(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
) -> DiagnosticStartResponse:
    try:
        attempt, topic, questions = await start_diagnostic_assessment(
            db=db,
            student_id=current_user.id,
            topic_id=topic_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    return DiagnosticStartResponse(
        attempt_id=attempt.id,
        topic_id=topic.id,
        topic_title=topic.title,
        assessment_type=attempt.assessment_type.value,
        status=attempt.status.value,
        total_questions=attempt.total_questions,
        questions=questions,
    )


@router.post(
    "/diagnostic/{attempt_id}/answer",
    response_model=DiagnosticAnswerResponse,
)
async def submit_diagnostic_question_answer(
    attempt_id: int,
    payload: DiagnosticAnswerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
) -> DiagnosticAnswerResponse:
    try:
        answer, question = await submit_diagnostic_answer(
            db=db,
            student_id=current_user.id,
            attempt_id=attempt_id,
            question_id=payload.question_id,
            submitted_answer=payload.answer,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return DiagnosticAnswerResponse(
        attempt_id=attempt_id,
        question_id=question.id,
        submitted_answer=answer.submitted_answer,
        is_correct=answer.is_correct,
        marks_awarded=answer.marks_awarded,
        explanation=question.explanation,
    )


@router.post(
    "/diagnostic/{attempt_id}/complete",
    response_model=DiagnosticResultResponse,
)
async def complete_diagnostic(
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
) -> DiagnosticResultResponse:
    try:
        attempt = await complete_diagnostic_assessment(
            db=db,
            student_id=current_user.id,
            attempt_id=attempt_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return DiagnosticResultResponse(
        attempt_id=attempt.id,
        topic_id=attempt.topic_id,
        correct_answers=attempt.correct_answers,
        total_questions=attempt.total_questions,
        score_percentage=attempt.score_percentage,
        status=attempt.status.value,
    )


@router.get(
    "/diagnostic/{attempt_id}/interpretation",
    response_model=DiagnosticInterpretationResponse,
)
async def get_diagnostic_interpretation(
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
) -> DiagnosticInterpretationResponse:
    try:
        result = await interpret_diagnostic_attempt(
            db=db,
            student_id=current_user.id,
            attempt_id=attempt_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return DiagnosticInterpretationResponse(**result)


@router.post(
    "/diagnostic/{attempt_id}/tutor/start",
    response_model=TutorStartResponse,
)
async def start_tutor(
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
) -> TutorStartResponse:
    try:
        tutor_message, topic_id = await start_tutor_session(
            db=db,
            student_id=current_user.id,
            attempt_id=attempt_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return TutorStartResponse(
        attempt_id=attempt_id,
        topic_id=topic_id,
        message=tutor_message,
    )


@router.post(
    "/diagnostic/{attempt_id}/tutor/message",
    response_model=TutorMessageResponse,
)
async def send_tutor_message(
    attempt_id: int,
    payload: TutorMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
) -> TutorMessageResponse:
    try:
        tutor_message, topic_id = await continue_tutor_session(
            db=db,
            student_id=current_user.id,
            attempt_id=attempt_id,
            student_message=payload.message,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return TutorMessageResponse(
        attempt_id=attempt_id,
        topic_id=topic_id,
        student_message=payload.message.strip(),
        tutor_message=tutor_message,
    )


@router.post(
    "/diagnostic/{diagnostic_attempt_id}/practice/start",
    response_model=PracticeStartResponse,
)
async def start_practice(
    diagnostic_attempt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
) -> PracticeStartResponse:
    try:
        (
            practice_attempt,
            diagnostic_attempt,
            topic,
            questions,
        ) = await start_practice_assessment(
            db=db,
            student_id=current_user.id,
            diagnostic_attempt_id=diagnostic_attempt_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return PracticeStartResponse(
        attempt_id=practice_attempt.id,
        diagnostic_attempt_id=diagnostic_attempt.id,
        topic_id=topic.id,
        topic_title=topic.title,
        assessment_type=practice_attempt.assessment_type.value,
        status=practice_attempt.status.value,
        total_questions=practice_attempt.total_questions,
        questions=questions,
    )


@router.post(
    "/practice/{attempt_id}/answer",
    response_model=PracticeAnswerResponse,
)
async def submit_practice_question_answer(
    attempt_id: int,
    payload: PracticeAnswerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
) -> PracticeAnswerResponse:
    try:
        answer, question = await submit_practice_answer(
            db=db,
            student_id=current_user.id,
            attempt_id=attempt_id,
            question_id=payload.question_id,
            submitted_answer=payload.submitted_answer,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return PracticeAnswerResponse(
        attempt_id=attempt_id,
        question_id=question.id,
        submitted_answer=answer.submitted_answer,
        is_correct=answer.is_correct,
        marks_awarded=answer.marks_awarded,
    )


@router.post(
    "/practice/{attempt_id}/complete",
    response_model=PracticeCompleteResponse,
)
async def complete_practice(
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
) -> PracticeCompleteResponse:
    try:
        attempt = await complete_practice_assessment(
            db=db,
            student_id=current_user.id,
            attempt_id=attempt_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return PracticeCompleteResponse(
        attempt_id=attempt.id,
        assessment_type=attempt.assessment_type.value,
        status=attempt.status.value,
        correct_answers=attempt.correct_answers,
        total_questions=attempt.total_questions,
        score_percentage=attempt.score_percentage,
        completed_at=attempt.completed_at,
    )


@router.get(
    "/diagnostic/{diagnostic_attempt_id}/improvement",
    response_model=LearningImprovementResponse,
)
async def get_learning_improvement(
    diagnostic_attempt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
) -> LearningImprovementResponse:
    try:
        result = await build_learning_improvement_result(
            db=db,
            student_id=current_user.id,
            diagnostic_attempt_id=diagnostic_attempt_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return LearningImprovementResponse(**result)
