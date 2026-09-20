from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.enums import DocumentType, UserRole
from app.models.user import User
from app.schemas.teacher import (
    TeacherClassLearningSummary,
    TeacherClassStudent,
    TeacherClassSummary,
    TeacherClassTopicPerformanceResponse,
    TeacherInsightContext,
    TeacherInsightResponse,
    TeacherDocumentSummary,
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

from app.services.document_processing import (
    process_document,
)
from app.services.document_storage import (
    build_document_storage_key,
    delete_document_file,
    save_document_bytes,
)
from app.services.teacher_documents import (
    create_teacher_assignment_document,
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

@router.post(
    "/documents",
    response_model=TeacherDocumentSummary,
    status_code=status.HTTP_201_CREATED,
)
async def upload_teacher_document(
    teaching_assignment_id: int = Form(...),
    title: str = Form(...),
    document_type: DocumentType = Form(...),
    topic_id: int | None = Form(None),
    academic_year: int | None = Form(None),
    exam_year: int | None = Form(None),
    paper_number: str | None = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.TEACHER)
    ),
) -> TeacherDocumentSummary:
    clean_title = title.strip()

    if not clean_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document title is required.",
        )

    original_filename = (
        file.filename or ""
    ).strip()

    if not original_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document filename is required.",
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document file cannot be empty.",
        )

    mime_type = (
        file.content_type
        or "application/octet-stream"
    )

    storage_key = build_document_storage_key(
        school_id=current_user.school_id,
        original_filename=original_filename,
    )

    try:
        # Authorization and curriculum scope are validated by
        # create_teacher_assignment_document. Validate before the
        # source file becomes durable by creating the record only
        # after its assignment has been checked.
        #
        # The file is written immediately before persistence because
        # the service commit must never leave a document record whose
        # source file was never stored.
        from app.services.teaching_assignments import (
            get_teacher_teaching_assignment,
        )

        assignment = await get_teacher_teaching_assignment(
            db=db,
            teacher_id=current_user.id,
            school_id=current_user.school_id,
            assignment_id=teaching_assignment_id,
        )

        if assignment is None:
            raise ValueError(
                "Active teaching assignment not found for this teacher."
            )

        save_document_bytes(
            storage_key=storage_key,
            content=content,
        )

        document = await create_teacher_assignment_document(
            db=db,
            teacher_id=current_user.id,
            school_id=current_user.school_id,
            teaching_assignment_id=teaching_assignment_id,
            topic_id=topic_id,
            title=clean_title,
            document_type=document_type,
            academic_year=academic_year,
            exam_year=exam_year,
            paper_number=(
                paper_number.strip()
                if paper_number
                else None
            ),
            original_filename=original_filename,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size=len(content),
        )

    except ValueError as exc:
        delete_document_file(storage_key)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception:
        delete_document_file(storage_key)
        raise

    try:
        await process_document(
            db,
            document.id,
        )
    except (ValueError, OSError):
        # Processing records its own failure state. Preserve the
        # source file so processing can be retried.
        pass

    await db.refresh(document)

    return document
