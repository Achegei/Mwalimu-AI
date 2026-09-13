from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.teacher import (
    TeacherClassLearningSummary,
    TeacherClassStudent,
    TeacherClassSummary,
    TeacherClassTopicPerformanceResponse,
    TeacherInsightContext,
    TeacherInsightResponse,
    TeacherStudentProgressResponse,
    TeacherWeakTopicsResponse,
)
from app.services.teacher_analytics import (
    build_teacher_insight_context,
    get_class_learning_summary,
    get_class_topic_performance,
    get_teacher_classes,
    identify_class_weak_topics,
)
from app.services.teacher_insights import (
    generate_teacher_insight,
)
from app.services.teacher_students import (
    get_teacher_class_students,
    get_teacher_student_progress,
)


router = APIRouter(
    prefix="/teacher",
    tags=["Teacher"],
)


@router.get(
    "/classes",
    response_model=list[TeacherClassSummary],
)
async def list_teacher_classes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.TEACHER)
    ),
) -> list[TeacherClassSummary]:
    classes = await get_teacher_classes(
        db=db,
        teacher_id=current_user.id,
    )

    return classes


@router.get(
    "/classes/{classroom_id}/summary",
    response_model=TeacherClassLearningSummary,
)
async def get_class_summary(
    classroom_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.TEACHER)
    ),
) -> TeacherClassLearningSummary:
    try:
        summary = await get_class_learning_summary(
            db=db,
            teacher_id=current_user.id,
            teacher_school_id=current_user.school_id,
            classroom_id=classroom_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    return TeacherClassLearningSummary(**summary)


@router.get(
    "/classes/{classroom_id}/topics",
    response_model=TeacherClassTopicPerformanceResponse,
)
async def get_class_topics(
    classroom_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.TEACHER)
    ),
) -> TeacherClassTopicPerformanceResponse:
    try:
        result = await get_class_topic_performance(
            db=db,
            teacher_id=current_user.id,
            teacher_school_id=current_user.school_id,
            classroom_id=classroom_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    return TeacherClassTopicPerformanceResponse(**result)


@router.get(
    "/classes/{classroom_id}/weak-topics",
    response_model=TeacherWeakTopicsResponse,
)
async def get_class_weak_topics(
    classroom_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.TEACHER)
    ),
) -> TeacherWeakTopicsResponse:
    try:
        result = await identify_class_weak_topics(
            db=db,
            teacher_id=current_user.id,
            teacher_school_id=current_user.school_id,
            classroom_id=classroom_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    return TeacherWeakTopicsResponse(**result)


@router.get(
    "/classes/{classroom_id}/insight",
    response_model=TeacherInsightResponse,
)
async def get_class_insight(
    classroom_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.TEACHER)
    ),
) -> TeacherInsightResponse:
    try:
        context_data = await build_teacher_insight_context(
            db=db,
            teacher_id=current_user.id,
            teacher_school_id=current_user.school_id,
            classroom_id=classroom_id,
        )

        context = TeacherInsightContext(
            **context_data,
        )

        insight = await generate_teacher_insight(
            context=context,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    return TeacherInsightResponse(
        context=context,
        insight=insight,
    )


@router.get(
    "/classes/{classroom_id}/students",
    response_model=list[TeacherClassStudent],
)
async def list_class_students(
    classroom_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.TEACHER)
    ),
) -> list[TeacherClassStudent]:
    try:
        students = await get_teacher_class_students(
            db=db,
            teacher_id=current_user.id,
            teacher_school_id=current_user.school_id,
            classroom_id=classroom_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    return [
        TeacherClassStudent(**student)
        for student in students
    ]


@router.get(
    "/classes/{classroom_id}/students/{student_id}/progress",
    response_model=TeacherStudentProgressResponse,
)
async def get_class_student_progress(
    classroom_id: int,
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.TEACHER)
    ),
) -> TeacherStudentProgressResponse:
    try:
        result = await get_teacher_student_progress(
            db=db,
            teacher_id=current_user.id,
            teacher_school_id=current_user.school_id,
            classroom_id=classroom_id,
            student_id=student_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    return TeacherStudentProgressResponse(**result)
