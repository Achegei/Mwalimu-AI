from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrollment import Enrollment
from app.models.enums import UserRole
from app.models.user import User
from app.services.progress import get_student_progress
from app.services.teacher_analytics import get_teacher_classroom


async def get_teacher_class_students(
    db: AsyncSession,
    teacher_id: int,
    teacher_school_id: int,
    classroom_id: int,
) -> list[dict]:
    classroom = await get_teacher_classroom(
        db=db,
        teacher_id=teacher_id,
        teacher_school_id=teacher_school_id,
        classroom_id=classroom_id,
    )

    if classroom is None:
        raise ValueError("Classroom not found.")

    result = await db.execute(
        select(
            User.id,
            User.full_name,
            User.login_id,
        )
        .join(
            Enrollment,
            Enrollment.student_id == User.id,
        )
        .where(
            Enrollment.classroom_id == classroom.id,
            Enrollment.is_active.is_(True),
            User.role == UserRole.STUDENT,
            User.school_id == teacher_school_id,
            User.is_active.is_(True),
        )
        .order_by(
            User.full_name.asc(),
            User.id.asc(),
        )
    )

    return [
        {
            "student_id": student_id,
            "full_name": full_name,
            "login_id": login_id,
        }
        for student_id, full_name, login_id in result.all()
    ]


async def get_teacher_student_progress(
    db: AsyncSession,
    teacher_id: int,
    teacher_school_id: int,
    classroom_id: int,
    student_id: int,
) -> dict:
    classroom = await get_teacher_classroom(
        db=db,
        teacher_id=teacher_id,
        teacher_school_id=teacher_school_id,
        classroom_id=classroom_id,
    )

    if classroom is None:
        raise ValueError("Classroom not found.")

    result = await db.execute(
        select(User)
        .join(
            Enrollment,
            Enrollment.student_id == User.id,
        )
        .where(
            User.id == student_id,
            User.role == UserRole.STUDENT,
            User.school_id == teacher_school_id,
            User.is_active.is_(True),
            Enrollment.classroom_id == classroom.id,
            Enrollment.is_active.is_(True),
        )
    )

    student = result.scalar_one_or_none()

    if student is None:
        raise ValueError("Student not found in this classroom.")

    progress = await get_student_progress(
        db=db,
        student_id=student.id,
        school_id=teacher_school_id,
        classroom_id=classroom.id,
    )

    return {
        "classroom_id": classroom.id,
        "classroom_name": classroom.name,
        "student": {
            "student_id": student.id,
            "full_name": student.full_name,
            "login_id": student.login_id,
        },
        "progress": progress,
    }
