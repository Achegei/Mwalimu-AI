from sqlalchemy import (
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class TeachingAssignment(TimestampMixin, Base):
    """
    Authoritative relationship describing which teacher teaches
    which subject to which classroom.

    A teacher may have many teaching assignments across subjects
    and classrooms.
    """

    __tablename__ = "teaching_assignments"

    __table_args__ = (
        UniqueConstraint(
            "teacher_id",
            "subject_id",
            "classroom_id",
            name=(
                "uq_teaching_assignment_"
                "teacher_subject_classroom"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    school_id: Mapped[int] = mapped_column(
        ForeignKey(
            "schools.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    teacher_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    subject_id: Mapped[int] = mapped_column(
        ForeignKey(
            "subjects.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    classroom_id: Mapped[int] = mapped_column(
        ForeignKey(
            "classrooms.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
