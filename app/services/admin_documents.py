from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Subject, Topic
from app.models.document import Document
from app.models.enums import (
    DocumentProcessingStatus,
    DocumentType,
)


async def validate_document_scope(
    db: AsyncSession,
    school_id: int,
    subject_id: int,
    topic_id: int | None,
    form_level: int,
) -> None:
    """
    Validate that document curriculum metadata belongs to the
    authenticated admin's school.

    A topic, when supplied, must belong to the selected subject
    and must match the document's form level.
    """

    subject_result = await db.execute(
        select(Subject).where(
            Subject.id == subject_id,
            Subject.school_id == school_id,
            Subject.is_active.is_(True),
        )
    )

    subject = subject_result.scalar_one_or_none()

    if subject is None:
        raise ValueError(
            "Active subject not found in this school."
        )

    if topic_id is None:
        return

    topic_result = await db.execute(
        select(Topic).where(
            Topic.id == topic_id,
            Topic.subject_id == subject_id,
            Topic.is_active.is_(True),
        )
    )

    topic = topic_result.scalar_one_or_none()

    if topic is None:
        raise ValueError(
            "Active topic not found for this subject."
        )

    if topic.form_level != form_level:
        raise ValueError(
            "Topic form level does not match document form level."
        )


async def create_school_document(
    db: AsyncSession,
    *,
    school_id: int,
    uploaded_by_id: int,
    subject_id: int,
    topic_id: int | None,
    title: str,
    document_type: DocumentType,
    form_level: int,
    academic_year: int | None,
    exam_year: int | None,
    paper_number: str | None,
    original_filename: str,
    storage_key: str,
    mime_type: str,
    file_size: int,
) -> Document:
    """
    Create a document catalog record after validating that its
    subject and optional topic belong to the admin's school.
    """

    await validate_document_scope(
        db=db,
        school_id=school_id,
        subject_id=subject_id,
        topic_id=topic_id,
        form_level=form_level,
    )

    document = Document(
        school_id=school_id,
        subject_id=subject_id,
        topic_id=topic_id,
        uploaded_by_id=uploaded_by_id,
        title=title,
        document_type=document_type,
        form_level=form_level,
        academic_year=academic_year,
        exam_year=exam_year,
        paper_number=paper_number,
        original_filename=original_filename,
        storage_key=storage_key,
        mime_type=mime_type,
        file_size=file_size,
        processing_status=(
            DocumentProcessingStatus.UPLOADED
        ),
        error_message=None,
        metadata_json=None,
        is_active=True,
    )

    db.add(document)

    await db.commit()
    await db.refresh(document)

    return document


async def get_school_documents(
    db: AsyncSession,
    school_id: int,
) -> list[Document]:
    """
    Return active documents belonging only to one school.
    """

    result = await db.execute(
        select(Document)
        .where(
            Document.school_id == school_id,
            Document.is_active.is_(True),
        )
        .order_by(
            Document.created_at.desc(),
            Document.id.desc(),
        )
    )

    return list(result.scalars().all())
