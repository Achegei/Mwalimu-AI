from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin
from app.models.enums import LearningEventType


class LearningEvent(TimestampMixin, Base):
    __tablename__ = "learning_events"

    id: Mapped[int] = mapped_column(primary_key=True)

    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    classroom_id: Mapped[int | None] = mapped_column(
        ForeignKey("classrooms.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    assessment_attempt_id: Mapped[int | None] = mapped_column(
        ForeignKey("assessment_attempts.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    question_id: Mapped[int | None] = mapped_column(
        ForeignKey("questions.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    event_type: Mapped[LearningEventType] = mapped_column(
        Enum(
            LearningEventType,
            name="learning_event_type",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        index=True,
        nullable=False,
    )

    event_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
    )
