from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import DifficultyLevel, QuestionType


class Subject(TimestampMixin, Base):
    __tablename__ = "subjects"

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "slug",
            name="uq_subject_school_slug",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(120),
        index=True,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )


class Topic(TimestampMixin, Base):
    __tablename__ = "topics"

    __table_args__ = (
        UniqueConstraint(
            "subject_id",
            "slug",
            name="uq_topic_subject_slug",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(120),
        index=True,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    form_level: Mapped[int] = mapped_column(
        Integer,
        default=2,
        index=True,
        nullable=False,
    )

    order_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )


class Question(TimestampMixin, Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)

    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    question_type: Mapped[QuestionType] = mapped_column(
        Enum(
            QuestionType,
            name="question_type",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )

    difficulty: Mapped[DifficultyLevel] = mapped_column(
        Enum(
            DifficultyLevel,
            name="difficulty_level",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=DifficultyLevel.MEDIUM,
        index=True,
        nullable=False,
    )

    prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    options: Mapped[list[Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    correct_answer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    marks: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
