from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AssessmentQuestion(TimestampMixin, Base):
    __tablename__ = "assessment_questions"

    __table_args__ = (
        UniqueConstraint(
            "assessment_attempt_id",
            "question_id",
            name="uq_assessment_question_attempt_question",
        ),
        UniqueConstraint(
            "assessment_attempt_id",
            "position",
            name="uq_assessment_question_attempt_position",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

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

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
