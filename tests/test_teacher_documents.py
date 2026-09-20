import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.classroom import Classroom
from app.models.content import Subject, Topic
from app.models.enums import (
    DocumentScope,
    DocumentType,
    UserRole,
)
from app.models.school import School
from app.models.teaching_assignment import TeachingAssignment
from app.models.user import User
from app.services.teacher_documents import (
    create_teacher_assignment_document,
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
        password_hash=hash_password("Teacher123!"),
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
) -> Topic:
    topic = Topic(
        subject_id=subject_id,
        title=title,
        slug=slug,
        form_level=form_level,
        order_index=1,
        is_active=True,
    )
    db.add(topic)
    await db.flush()
    return topic


async def create_assignment(
    db: AsyncSession,
    *,
    school_id: int,
    teacher_id: int,
    subject_id: int,
    classroom_id: int,
    is_active: bool = True,
) -> TeachingAssignment:
    assignment = TeachingAssignment(
        school_id=school_id,
        teacher_id=teacher_id,
        subject_id=subject_id,
        classroom_id=classroom_id,
        is_active=is_active,
    )
    db.add(assignment)
    await db.flush()
    return assignment


async def build_assignment_context(
    db: AsyncSession,
    *,
    prefix: str,
    form_level: int = 2,
):
    school = await create_school(
        db,
        name=f"{prefix} School",
        code=f"{prefix.upper()}-001",
    )

    teacher = await create_teacher(
        db,
        school_id=school.id,
        login_id=f"{prefix}-teacher",
        full_name=f"{prefix.title()} Teacher",
    )

    subject = await create_subject(
        db,
        school_id=school.id,
        name=f"{prefix.title()} Biology",
        slug=f"{prefix}-biology",
    )

    classroom = await create_classroom(
        db,
        school_id=school.id,
        name=f"{prefix.title()} Form {form_level}",
        form_level=form_level,
    )

    assignment = await create_assignment(
        db,
        school_id=school.id,
        teacher_id=teacher.id,
        subject_id=subject.id,
        classroom_id=classroom.id,
    )

    return school, teacher, subject, classroom, assignment


async def test_teacher_creates_assignment_scoped_document(
    db_session: AsyncSession,
):
    (
        school,
        teacher,
        subject,
        classroom,
        assignment,
    ) = await build_assignment_context(
        db_session,
        prefix="create-document",
        form_level=3,
    )

    topic = await create_topic(
        db_session,
        subject_id=subject.id,
        title="Cell Biology",
        slug="cell-biology",
        form_level=3,
    )

    await db_session.commit()

    document = await create_teacher_assignment_document(
        db_session,
        teacher_id=teacher.id,
        school_id=school.id,
        teaching_assignment_id=assignment.id,
        topic_id=topic.id,
        title="Cell Biology Teacher Notes",
        document_type=DocumentType.TEACHER_NOTES,
        academic_year=2026,
        exam_year=None,
        paper_number=None,
        original_filename="cell-biology.txt",
        storage_key="teacher/create-document/cell-biology.txt",
        mime_type="text/plain",
        file_size=128,
    )

    assert document.school_id == school.id
    assert document.subject_id == subject.id
    assert document.form_level == classroom.form_level
    assert document.topic_id == topic.id

    assert document.scope == DocumentScope.TEACHING_ASSIGNMENT
    assert document.teaching_assignment_id == assignment.id
    assert document.uploaded_by_id == teacher.id


async def test_teacher_cannot_use_another_teachers_assignment(
    db_session: AsyncSession,
):
    (
        school,
        owner,
        subject,
        classroom,
        assignment,
    ) = await build_assignment_context(
        db_session,
        prefix="foreign-assignment",
    )

    other_teacher = await create_teacher(
        db_session,
        school_id=school.id,
        login_id="foreign-assignment-other",
        full_name="Other Teacher",
    )

    await db_session.commit()

    with pytest.raises(
        ValueError,
        match="Active teaching assignment not found",
    ):
        await create_teacher_assignment_document(
            db_session,
            teacher_id=other_teacher.id,
            school_id=school.id,
            teaching_assignment_id=assignment.id,
            topic_id=None,
            title="Unauthorized Notes",
            document_type=DocumentType.TEACHER_NOTES,
            academic_year=2026,
            exam_year=None,
            paper_number=None,
            original_filename="unauthorized.txt",
            storage_key="teacher/foreign-assignment/unauthorized.txt",
            mime_type="text/plain",
            file_size=64,
        )

    assert owner.id != other_teacher.id
    assert assignment.subject_id == subject.id
    assert assignment.classroom_id == classroom.id


async def test_inactive_assignment_cannot_create_document(
    db_session: AsyncSession,
):
    (
        school,
        teacher,
        subject,
        classroom,
        assignment,
    ) = await build_assignment_context(
        db_session,
        prefix="inactive-document",
    )

    assignment.is_active = False
    await db_session.commit()

    with pytest.raises(
        ValueError,
        match="Active teaching assignment not found",
    ):
        await create_teacher_assignment_document(
            db_session,
            teacher_id=teacher.id,
            school_id=school.id,
            teaching_assignment_id=assignment.id,
            topic_id=None,
            title="Inactive Assignment Notes",
            document_type=DocumentType.TEACHER_NOTES,
            academic_year=2026,
            exam_year=None,
            paper_number=None,
            original_filename="inactive.txt",
            storage_key="teacher/inactive-document/inactive.txt",
            mime_type="text/plain",
            file_size=64,
        )

    assert assignment.subject_id == subject.id
    assert assignment.classroom_id == classroom.id


async def test_topic_must_belong_to_assignment_subject(
    db_session: AsyncSession,
):
    (
        school,
        teacher,
        _subject,
        _classroom,
        assignment,
    ) = await build_assignment_context(
        db_session,
        prefix="subject-boundary",
    )

    foreign_subject = await create_subject(
        db_session,
        school_id=school.id,
        name="Chemistry",
        slug="subject-boundary-chemistry",
    )

    foreign_topic = await create_topic(
        db_session,
        subject_id=foreign_subject.id,
        title="Atomic Structure",
        slug="atomic-structure",
        form_level=2,
    )

    await db_session.commit()

    with pytest.raises(
        ValueError,
        match="Active topic not found",
    ):
        await create_teacher_assignment_document(
            db_session,
            teacher_id=teacher.id,
            school_id=school.id,
            teaching_assignment_id=assignment.id,
            topic_id=foreign_topic.id,
            title="Wrong Subject Notes",
            document_type=DocumentType.TEACHER_NOTES,
            academic_year=2026,
            exam_year=None,
            paper_number=None,
            original_filename="wrong-subject.txt",
            storage_key="teacher/subject-boundary/wrong-subject.txt",
            mime_type="text/plain",
            file_size=64,
        )


async def test_topic_form_level_must_match_assignment_classroom(
    db_session: AsyncSession,
):
    (
        school,
        teacher,
        subject,
        _classroom,
        assignment,
    ) = await build_assignment_context(
        db_session,
        prefix="form-boundary",
        form_level=2,
    )

    wrong_form_topic = await create_topic(
        db_session,
        subject_id=subject.id,
        title="Form 3 Genetics",
        slug="form-3-genetics",
        form_level=3,
    )

    await db_session.commit()

    with pytest.raises(
        ValueError,
        match="Topic form level does not match",
    ):
        await create_teacher_assignment_document(
            db_session,
            teacher_id=teacher.id,
            school_id=school.id,
            teaching_assignment_id=assignment.id,
            topic_id=wrong_form_topic.id,
            title="Wrong Form Notes",
            document_type=DocumentType.TEACHER_NOTES,
            academic_year=2026,
            exam_year=None,
            paper_number=None,
            original_filename="wrong-form.txt",
            storage_key="teacher/form-boundary/wrong-form.txt",
            mime_type="text/plain",
            file_size=64,
        )
