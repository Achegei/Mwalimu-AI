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


async def bulk_import_school_students(
    db: AsyncSession,
    school_id: int,
    classroom_id: int,
    rows: list[dict[str, str]],
) -> dict:
    """
    Import students into a school classroom.

    Existing active students in the same school are reused.
    Existing active enrollments are skipped. Invalid rows are
    reported individually without preventing valid rows from
    being processed.
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

    created = 0
    enrolled = 0
    skipped = 0
    failed = 0
    results: list[dict] = []

    for index, raw_row in enumerate(
        rows,
        start=2,
    ):
        full_name = str(
            raw_row.get("full_name") or ""
        ).strip()
        login_id = str(
            raw_row.get("login_id") or ""
        ).strip()
        password = str(
            raw_row.get("password") or ""
        ).strip()

        if not login_id:
            failed += 1
            results.append(
                {
                    "row_number": index,
                    "login_id": "",
                    "status": "failed",
                    "message": "Login ID is required.",
                }
            )
            continue

        if not full_name:
            failed += 1
            results.append(
                {
                    "row_number": index,
                    "login_id": login_id,
                    "status": "failed",
                    "message": "Full name is required.",
                }
            )
            continue

        user_result = await db.execute(
            select(User).where(
                User.login_id == login_id,
            )
        )

        student = user_result.scalar_one_or_none()
        student_created = False

        if student is not None:
            if student.school_id != school_id:
                failed += 1
                results.append(
                    {
                        "row_number": index,
                        "login_id": login_id,
                        "status": "failed",
                        "message": (
                            "Login ID belongs to another school."
                        ),
                    }
                )
                continue

            if student.role != UserRole.STUDENT:
                failed += 1
                results.append(
                    {
                        "row_number": index,
                        "login_id": login_id,
                        "status": "failed",
                        "message": (
                            "Login ID does not belong to a student."
                        ),
                    }
                )
                continue

            if not student.is_active:
                failed += 1
                results.append(
                    {
                        "row_number": index,
                        "login_id": login_id,
                        "status": "failed",
                        "message": (
                            "Student account is inactive."
                        ),
                    }
                )
                continue

        else:
            if not password:
                failed += 1
                results.append(
                    {
                        "row_number": index,
                        "login_id": login_id,
                        "status": "failed",
                        "message": (
                            "Password is required for a new student."
                        ),
                    }
                )
                continue

            if len(password) < 6:
                failed += 1
                results.append(
                    {
                        "row_number": index,
                        "login_id": login_id,
                        "status": "failed",
                        "message": (
                            "Password must contain at least "
                            "6 characters."
                        ),
                    }
                )
                continue

            student = User(
                school_id=school_id,
                login_id=login_id,
                full_name=full_name,
                role=UserRole.STUDENT,
                password_hash=hash_password(password),
                is_active=True,
            )

            db.add(student)
            await db.flush()

            student_created = True

        enrollment_result = await db.execute(
            select(Enrollment).where(
                Enrollment.classroom_id == classroom_id,
                Enrollment.student_id == student.id,
            )
        )

        existing_enrollment = (
            enrollment_result.scalar_one_or_none()
        )

        if existing_enrollment is not None:
            if existing_enrollment.is_active:
                if student_created:
                    await db.rollback()
                    raise RuntimeError(
                        "Unexpected enrollment state during import."
                    )

                skipped += 1
                results.append(
                    {
                        "row_number": index,
                        "login_id": login_id,
                        "status": "skipped",
                        "message": (
                            "Student is already enrolled "
                            "in this classroom."
                        ),
                    }
                )
                continue

            existing_enrollment.is_active = True

        else:
            db.add(
                Enrollment(
                    classroom_id=classroom_id,
                    student_id=student.id,
                    is_active=True,
                )
            )

        if student_created:
            created += 1

        enrolled += 1

        results.append(
            {
                "row_number": index,
                "login_id": login_id,
                "status": "enrolled",
                "message": (
                    "Student created and enrolled."
                    if student_created
                    else "Existing student enrolled."
                ),
            }
        )

    await db.commit()

    return {
        "total_rows": len(rows),
        "created": created,
        "enrolled": enrolled,
        "skipped": skipped,
        "failed": failed,
        "rows": results,
    }

