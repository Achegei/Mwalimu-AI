from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class TutorMessage(TimestampMixin, Base):
    __tablename__ = "tutor_messages"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    classroom_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "classrooms.id",
            ondelete="SET NULL",
        ),
        index=True,
        nullable=True,
    )

    topic_id: Mapped[int] = mapped_column(
        ForeignKey(
            "topics.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    assessment_attempt_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessment_attempts.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
