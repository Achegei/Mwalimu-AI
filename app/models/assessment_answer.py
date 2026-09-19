from sqlalchemy import Boolean, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AssessmentAnswer(TimestampMixin, Base):
    __tablename__ = "assessment_answers"

    __table_args__ = (
        UniqueConstraint(
            "assessment_attempt_id",
            "question_id",
            name="uq_assessment_answer_attempt_question",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    assessment_attempt_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessment_attempts.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    question_id: Mapped[int] = mapped_column(
        ForeignKey(
            "questions.id",
            ondelete="RESTRICT",
        ),
        index=True,
        nullable=False,
    )

    submitted_answer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    is_correct: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    marks_awarded: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
