from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.classroom import Classroom
from app.models.enrollment import Enrollment
from app.models.enums import UserRole
from app.models.user import User


async def get_school_users(
    db: AsyncSession,
    school_id: int,
) -> list[User]:
    """
    Return users belonging only to the authenticated admin's school.
    """

    result = await db.execute(
        select(User)
        .where(
            User.school_id == school_id,
        )
        .order_by(
            User.full_name.asc(),
            User.id.asc(),
        )
    )

    return list(result.scalars().all())


async def create_school_user(
    db: AsyncSession,
    school_id: int,
    login_id: str,
    full_name: str,
    role: UserRole,
    password: str,
) -> User:
    """
    Create a teacher or student owned by the authenticated
    admin's school.
    """

    existing_result = await db.execute(
        select(User.id).where(
            User.login_id == login_id,
        )
    )

    if existing_result.scalar_one_or_none() is not None:
        raise ValueError("A user with this login ID already exists.")

    user = User(
        school_id=school_id,
        login_id=login_id,
        full_name=full_name,
        role=role,
        password_hash=hash_password(password),
        is_active=True,
    )

    db.add(user)

    await db.commit()
    await db.refresh(user)

    return user


async def get_school_classrooms(
    db: AsyncSession,
    school_id: int,
) -> list[Classroom]:
    """
    Return classrooms belonging only to the authenticated
    admin's school.
    """

    result = await db.execute(
        select(Classroom)
        .where(
            Classroom.school_id == school_id,
        )
        .order_by(
            Classroom.academic_year.desc(),
            Classroom.form_level.asc(),
            Classroom.name.asc(),
            Classroom.id.asc(),
        )
    )

    return list(result.scalars().all())


async def create_school_classroom(
    db: AsyncSession,
    school_id: int,
    name: str,
    form_level: int,
    academic_year: int,
    teacher_id: int | None,
) -> Classroom:
    """
    Create a classroom owned by the authenticated admin's school.

    When a teacher is supplied, the teacher must be an active
    teacher belonging to the same school.
    """

    if teacher_id is not None:
        teacher_result = await db.execute(
            select(User).where(
                User.id == teacher_id,
                User.school_id == school_id,
                User.role == UserRole.TEACHER,
                User.is_active.is_(True),
            )
        )

        teacher = teacher_result.scalar_one_or_none()

        if teacher is None:
            raise ValueError(
                "Teacher not found in this school."
            )

    existing_result = await db.execute(
        select(Classroom.id).where(
            Classroom.school_id == school_id,
            Classroom.name == name,
            Classroom.academic_year == academic_year,
        )
    )

    if existing_result.scalar_one_or_none() is not None:
        raise ValueError(
            "A classroom with this name and academic year "
            "already exists."
        )

    classroom = Classroom(
        school_id=school_id,
        teacher_id=teacher_id,
        name=name,
        form_level=form_level,
        academic_year=academic_year,
    )

    db.add(classroom)

    await db.commit()
    await db.refresh(classroom)

    return classroom


async def get_school_classroom_students(
    db: AsyncSession,
    school_id: int,
    classroom_id: int,
) -> list[dict]:
    """
    Return active enrollments for a classroom belonging
    to the authenticated admin's school.
    """

    classroom_result = await db.execute(
        select(Classroom.id).where(
            Classroom.id == classroom_id,
            Classroom.school_id == school_id,
        )
    )

    if classroom_result.scalar_one_or_none() is None:
        raise ValueError(
            "Classroom not found in this school."
        )

    result = await db.execute(
        select(
            User.id,
            User.login_id,
            User.full_name,
            Enrollment.is_active,
        )
        .join(
            Enrollment,
            Enrollment.student_id == User.id,
        )
        .where(
            Enrollment.classroom_id == classroom_id,
            User.school_id == school_id,
            User.role == UserRole.STUDENT,
        )
        .order_by(
            User.full_name.asc(),
            User.id.asc(),
        )
    )

    return [
        {
            "student_id": row.id,
            "login_id": row.login_id,
            "full_name": row.full_name,
            "is_active": row.is_active,
        }
        for row in result.all()
    ]


async def enroll_school_student(
    db: AsyncSession,
    school_id: int,
    classroom_id: int,
    student_id: int,
) -> dict:
    """
    Enroll an active student into a classroom.

    Both the classroom and student must belong to the
    authenticated admin's school.
    """

    classroom_result = await db.execute(
        select(Classroom.id).where(
            Classroom.id == classroom_id,
            Classroom.school_id == school_id,
        )
    )

    if classroom_result.scalar_one_or_none() is None:
        raise ValueError(
            "Classroom not found in this school."
        )

    student_result = await db.execute(
        select(User).where(
            User.id == student_id,
            User.school_id == school_id,
            User.role == UserRole.STUDENT,
            User.is_active.is_(True),
        )
    )

    student = student_result.scalar_one_or_none()

    if student is None:
        raise ValueError(
            "Active student not found in this school."
        )

    enrollment_result = await db.execute(
        select(Enrollment).where(
            Enrollment.classroom_id == classroom_id,
            Enrollment.student_id == student_id,
        )
    )

    existing_enrollment = (
        enrollment_result.scalar_one_or_none()
    )

    if existing_enrollment is not None:
        raise ValueError(
            "Student is already enrolled in this classroom."
        )

    enrollment = Enrollment(
        classroom_id=classroom_id,
        student_id=student_id,
        is_active=True,
    )

    db.add(enrollment)

    await db.commit()
    await db.refresh(enrollment)

    return {
        "student_id": student.id,
        "login_id": student.login_id,
        "full_name": student.full_name,
        "is_active": enrollment.is_active,
    }

