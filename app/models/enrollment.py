from sqlalchemy import Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Enrollment(TimestampMixin, Base):
    __tablename__ = "enrollments"

    __table_args__ = (
        UniqueConstraint(
            "classroom_id",
            "student_id",
            name="uq_enrollment_classroom_student",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    classroom_id: Mapped[int] = mapped_column(
        ForeignKey("classrooms.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
