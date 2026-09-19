from datetime import datetime

from sqlalchemy import Enum, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from app.models.base import Base, TimestampMixin
from app.models.enums import AssessmentStatus, AssessmentType


class AssessmentAttempt(TimestampMixin, Base):
    __tablename__ = "assessment_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)

    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    classroom_id: Mapped[int | None] = mapped_column(
        ForeignKey("classrooms.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    assessment_type: Mapped[AssessmentType] = mapped_column(
        Enum(
            AssessmentType,
            name="assessment_type",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        index=True,
        nullable=False,
    )

    status: Mapped[AssessmentStatus] = mapped_column(
        Enum(
            AssessmentStatus,
            name="assessment_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=AssessmentStatus.IN_PROGRESS,
        index=True,
        nullable=False,
    )

    correct_answers: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    total_questions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    score_percentage: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
