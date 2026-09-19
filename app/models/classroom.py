from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Classroom(TimestampMixin, Base):
    __tablename__ = "classrooms"

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "name",
            "academic_year",
            name="uq_classroom_school_name_year",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    form_level: Mapped[int] = mapped_column(
        Integer,
        default=2,
        nullable=False,
    )

    academic_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
