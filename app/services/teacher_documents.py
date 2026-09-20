from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.classroom import Classroom
from app.models.content import Topic
from app.models.document import Document
from app.models.enums import (
    DocumentProcessingStatus,
    DocumentScope,
    DocumentType,
)
from app.services.teaching_assignments import (
    get_teacher_teaching_assignment,
)


async def create_teacher_assignment_document(
    db: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
    teaching_assignment_id: int,
    topic_id: int | None,
    title: str,
    document_type: DocumentType,
    academic_year: int | None,
    exam_year: int | None,
    paper_number: str | None,
    original_filename: str,
    storage_key: str,
    mime_type: str,
    file_size: int,
) -> Document:
    """
    Create a document owned by one teaching assignment.

    The teaching assignment is the authoritative source for the
    document's school, subject, classroom, and teacher scope.
    """

    assignment = await get_teacher_teaching_assignment(
        db=db,
        teacher_id=teacher_id,
        school_id=school_id,
        assignment_id=teaching_assignment_id,
    )

    if assignment is None:
        raise ValueError(
            "Active teaching assignment not found for this teacher."
        )

    classroom_result = await db.execute(
        select(Classroom).where(
            Classroom.id == assignment.classroom_id,
            Classroom.school_id == school_id,
        )
    )

    classroom = classroom_result.scalar_one_or_none()

    if classroom is None:
        raise ValueError(
            "Teaching assignment classroom not found in this school."
        )

    if topic_id is not None:
        topic_result = await db.execute(
            select(Topic).where(
                Topic.id == topic_id,
                Topic.subject_id == assignment.subject_id,
                Topic.is_active.is_(True),
            )
        )

        topic = topic_result.scalar_one_or_none()

        if topic is None:
            raise ValueError(
                "Active topic not found for this teaching assignment."
            )

        if topic.form_level != classroom.form_level:
            raise ValueError(
                "Topic form level does not match teaching assignment "
                "classroom form level."
            )

    document = Document(
        school_id=assignment.school_id,
        subject_id=assignment.subject_id,
        topic_id=topic_id,
        scope=DocumentScope.TEACHING_ASSIGNMENT,
        teaching_assignment_id=assignment.id,
        uploaded_by_id=teacher_id,
        title=title,
        document_type=document_type,
        form_level=classroom.form_level,
        academic_year=academic_year,
        exam_year=exam_year,
        paper_number=paper_number,
        original_filename=original_filename,
        storage_key=storage_key,
        mime_type=mime_type,
        file_size=file_size,
        processing_status=DocumentProcessingStatus.UPLOADED,
        error_message=None,
        metadata_json=None,
        is_active=True,
    )

    db.add(document)

    await db.commit()
    await db.refresh(document)

    return document
