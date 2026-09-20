from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    DocumentProcessingStatus,
    DocumentScope,
    DocumentType,
)


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)

    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    scope: Mapped[DocumentScope] = mapped_column(
        Enum(
            DocumentScope,
            name="document_scope",
            values_callable=lambda enum: [
                item.value for item in enum
            ],
        ),
        default=DocumentScope.COMMON,
        index=True,
        nullable=False,
    )

    teaching_assignment_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "teaching_assignments.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=True,
    )

    uploaded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    title: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
    )

    document_type: Mapped[DocumentType] = mapped_column(
        Enum(
            DocumentType,
            name="document_type",
            values_callable=lambda enum: [
                item.value for item in enum
            ],
        ),
        index=True,
        nullable=False,
    )

    form_level: Mapped[int] = mapped_column(
        Integer,
        index=True,
        nullable=False,
    )

    academic_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    exam_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    paper_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    storage_key: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        nullable=False,
    )

    mime_type: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    processing_status: Mapped[
        DocumentProcessingStatus
    ] = mapped_column(
        Enum(
            DocumentProcessingStatus,
            name="document_processing_status",
            values_callable=lambda enum: [
                item.value for item in enum
            ],
        ),
        default=DocumentProcessingStatus.UPLOADED,
        index=True,
        nullable=False,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
