import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.classroom import Classroom
from app.models.content import Subject, Topic
from app.models.enums import UserRole
from app.models.school import School
from app.models.teaching_assignment import TeachingAssignment
from app.models.user import User
from app.core.security import hash_password
from app.services.teaching_assignments import (
    get_teacher_teaching_assignment,
    get_teacher_teaching_assignments,
)


pytestmark = pytest.mark.asyncio


async def create_school(
    db: AsyncSession,
    *,
    name: str,
    code: str,
) -> School:
    school = School(
        name=name,
        code=code,
        is_active=True,
    )
    db.add(school)
    await db.flush()
    return school


async def create_teacher(
    db: AsyncSession,
    *,
    school_id: int,
    login_id: str,
    full_name: str,
) -> User:
    teacher = User(
        school_id=school_id,
        login_id=login_id,
        full_name=full_name,
        role=UserRole.TEACHER,
        password_hash=hash_password(
            "Teacher123!"
        ),
        is_active=True,
    )
    db.add(teacher)
    await db.flush()
    return teacher


async def create_subject(
    db: AsyncSession,
    *,
    school_id: int,
    name: str,
    slug: str,
) -> Subject:
    subject = Subject(
        school_id=school_id,
        name=name,
        slug=slug,
        is_active=True,
    )
    db.add(subject)
    await db.flush()
    return subject


async def create_classroom(
    db: AsyncSession,
    *,
    school_id: int,
    name: str,
    form_level: int = 2,
    academic_year: int = 2026,
) -> Classroom:
    classroom = Classroom(
        school_id=school_id,
        name=name,
        form_level=form_level,
        academic_year=academic_year,
    )
    db.add(classroom)
    await db.flush()
    return classroom


async def create_topic(
    db: AsyncSession,
    *,
    subject_id: int,
    title: str,
    slug: str,
    form_level: int = 2,
    order_index: int = 1,
) -> Topic:
    topic = Topic(
        subject_id=subject_id,
        title=title,
        slug=slug,
        form_level=form_level,
        order_index=order_index,
        is_active=True,
    )
    db.add(topic)
    await db.flush()
    return topic


async def test_assignment_is_authoritative_teacher_scope(
    db_session: AsyncSession,
):
    school = await create_school(
        db_session,
        name="Assignment Scope School",
        code="ASSIGNMENT-SCOPE-001",
    )

    teacher = await create_teacher(
        db_session,
        school_id=school.id,
        login_id="assignment-teacher",
        full_name="Assignment Teacher",
    )

    mathematics = await create_subject(
        db_session,
        school_id=school.id,
        name="Mathematics",
        slug="mathematics-assignment-scope",
    )

    biology = await create_subject(
        db_session,
        school_id=school.id,
        name="Biology",
        slug="biology-assignment-scope",
    )

    classroom = await create_classroom(
        db_session,
        school_id=school.id,
        name="Form 2A",
    )

    mathematics_assignment = TeachingAssignment(
        school_id=school.id,
        teacher_id=teacher.id,
        subject_id=mathematics.id,
        classroom_id=classroom.id,
        is_active=True,
    )

    biology_assignment = TeachingAssignment(
        school_id=school.id,
        teacher_id=teacher.id,
        subject_id=biology.id,
        classroom_id=classroom.id,
        is_active=True,
    )

    db_session.add_all(
        [
            mathematics_assignment,
            biology_assignment,
        ]
    )
    await db_session.commit()

    assignments = await get_teacher_teaching_assignments(
        db=db_session,
        teacher_id=teacher.id,
        school_id=school.id,
    )

    assert len(assignments) == 2

    assignment_ids = {
        assignment.id
        for assignment in assignments
    }

    assert mathematics_assignment.id in assignment_ids
    assert biology_assignment.id in assignment_ids

    resolved = await get_teacher_teaching_assignment(
        db=db_session,
        teacher_id=teacher.id,
        school_id=school.id,
        assignment_id=mathematics_assignment.id,
    )

    assert resolved is not None
    assert resolved.classroom_id == classroom.id
    assert resolved.subject_id == mathematics.id


async def test_assignment_subject_defines_topic_scope(
    db_session: AsyncSession,
):
    school = await create_school(
        db_session,
        name="Topic Scope School",
        code="TOPIC-SCOPE-001",
    )

    teacher = await create_teacher(
        db_session,
        school_id=school.id,
        login_id="topic-scope-teacher",
        full_name="Topic Scope Teacher",
    )

    mathematics = await create_subject(
        db_session,
        school_id=school.id,
        name="Mathematics",
        slug="mathematics-topic-scope",
    )

    biology = await create_subject(
        db_session,
        school_id=school.id,
        name="Biology",
        slug="biology-topic-scope",
    )

    classroom = await create_classroom(
        db_session,
        school_id=school.id,
        name="Form 2B",
    )

    math_topic = await create_topic(
        db_session,
        subject_id=mathematics.id,
        title="Algebra",
        slug="algebra-assignment-scope",
    )

    biology_topic = await create_topic(
        db_session,
        subject_id=biology.id,
        title="Cell Biology",
        slug="cell-biology-assignment-scope",
    )

    assignment = TeachingAssignment(
        school_id=school.id,
        teacher_id=teacher.id,
        subject_id=mathematics.id,
        classroom_id=classroom.id,
        is_active=True,
    )

    db_session.add(assignment)
    await db_session.commit()

    resolved = await get_teacher_teaching_assignment(
        db=db_session,
        teacher_id=teacher.id,
        school_id=school.id,
        assignment_id=assignment.id,
    )

    assert resolved is not None
    assert resolved.subject_id == mathematics.id

    assert math_topic.subject_id == resolved.subject_id
    assert biology_topic.subject_id != resolved.subject_id


async def test_inactive_assignment_cannot_authorize_teacher_scope(
    db_session: AsyncSession,
):
    school = await create_school(
        db_session,
        name="Inactive Scope School",
        code="INACTIVE-SCOPE-001",
    )

    teacher = await create_teacher(
        db_session,
        school_id=school.id,
        login_id="inactive-scope-teacher",
        full_name="Inactive Scope Teacher",
    )

    subject = await create_subject(
        db_session,
        school_id=school.id,
        name="Mathematics",
        slug="inactive-scope-mathematics",
    )

    classroom = await create_classroom(
        db_session,
        school_id=school.id,
        name="Form 2C",
    )

    assignment = TeachingAssignment(
        school_id=school.id,
        teacher_id=teacher.id,
        subject_id=subject.id,
        classroom_id=classroom.id,
        is_active=False,
    )

    db_session.add(assignment)
    await db_session.commit()

    resolved = await get_teacher_teaching_assignment(
        db=db_session,
        teacher_id=teacher.id,
        school_id=school.id,
        assignment_id=assignment.id,
    )

    assert resolved is None
