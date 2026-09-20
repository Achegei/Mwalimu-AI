from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.classroom import Classroom
from app.models.content import Subject
from app.models.enums import UserRole
from app.models.teaching_assignment import TeachingAssignment
from app.models.user import User


async def get_school_teaching_assignments(
    db: AsyncSession,
    school_id: int,
) -> list[TeachingAssignment]:
    """
    Return teaching assignments belonging only to one school.
    """

    result = await db.execute(
        select(TeachingAssignment)
        .where(
            TeachingAssignment.school_id == school_id,
        )
        .order_by(
            TeachingAssignment.teacher_id.asc(),
            TeachingAssignment.subject_id.asc(),
            TeachingAssignment.classroom_id.asc(),
            TeachingAssignment.id.asc(),
        )
    )

    return list(result.scalars().all())


async def create_teaching_assignment(
    db: AsyncSession,
    *,
    school_id: int,
    teacher_id: int,
    subject_id: int,
    classroom_id: int,
) -> TeachingAssignment:
    """
    Assign an active teacher to teach an active subject
    in a classroom belonging to the same school.
    """

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
            "Active teacher not found in this school."
        )

    subject_result = await db.execute(
        select(Subject).where(
            Subject.id == subject_id,
            Subject.school_id == school_id,
            Subject.is_active.is_(True),
        )
    )

    subject = subject_result.scalar_one_or_none()

    if subject is None:
        raise ValueError(
            "Active subject not found in this school."
        )

    classroom_result = await db.execute(
        select(Classroom).where(
            Classroom.id == classroom_id,
            Classroom.school_id == school_id,
        )
    )

    classroom = classroom_result.scalar_one_or_none()

    if classroom is None:
        raise ValueError(
            "Classroom not found in this school."
        )

    existing_result = await db.execute(
        select(TeachingAssignment).where(
            TeachingAssignment.teacher_id == teacher_id,
            TeachingAssignment.subject_id == subject_id,
            TeachingAssignment.classroom_id == classroom_id,
        )
    )

    existing_assignment = (
        existing_result.scalar_one_or_none()
    )

    if existing_assignment is not None:
        if existing_assignment.school_id != school_id:
            raise ValueError(
                "Teaching assignment belongs to another school."
            )

        if existing_assignment.is_active:
            raise ValueError(
                "Teacher is already assigned to this subject "
                "and classroom."
            )

        existing_assignment.is_active = True

        await db.commit()
        await db.refresh(existing_assignment)

        return existing_assignment

    assignment = TeachingAssignment(
        school_id=school_id,
        teacher_id=teacher_id,
        subject_id=subject_id,
        classroom_id=classroom_id,
        is_active=True,
    )

    db.add(assignment)

    await db.commit()
    await db.refresh(assignment)

    return assignment


async def deactivate_teaching_assignment(
    db: AsyncSession,
    *,
    school_id: int,
    assignment_id: int,
) -> TeachingAssignment:
    """
    Deactivate a teaching assignment without deleting its history.
    """

    result = await db.execute(
        select(TeachingAssignment).where(
            TeachingAssignment.id == assignment_id,
            TeachingAssignment.school_id == school_id,
        )
    )

    assignment = result.scalar_one_or_none()

    if assignment is None:
        raise ValueError(
            "Teaching assignment not found in this school."
        )

    if not assignment.is_active:
        raise ValueError(
            "Teaching assignment is already inactive."
        )

    assignment.is_active = False

    await db.commit()
    await db.refresh(assignment)

    return assignment


async def get_teacher_teaching_assignment(
    db: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
    assignment_id: int,
) -> TeachingAssignment | None:
    """
    Return one active teaching assignment only when it belongs
    to the authenticated teacher and school.

    This is the authoritative authorization primitive for
    teacher academic operations.
    """

    result = await db.execute(
        select(TeachingAssignment).where(
            TeachingAssignment.id == assignment_id,
            TeachingAssignment.teacher_id == teacher_id,
            TeachingAssignment.school_id == school_id,
            TeachingAssignment.is_active.is_(True),
        )
    )

    return result.scalar_one_or_none()


async def get_teacher_teaching_assignments(
    db: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
) -> list[TeachingAssignment]:
    """
    Return all active teaching assignments belonging to the
    authenticated teacher within their school.
    """

    result = await db.execute(
        select(TeachingAssignment)
        .where(
            TeachingAssignment.teacher_id == teacher_id,
            TeachingAssignment.school_id == school_id,
            TeachingAssignment.is_active.is_(True),
        )
        .order_by(
            TeachingAssignment.classroom_id.asc(),
            TeachingAssignment.subject_id.asc(),
            TeachingAssignment.id.asc(),
        )
    )

    return list(result.scalars().all())
