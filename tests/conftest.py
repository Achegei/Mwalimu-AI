import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

import app.models
from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models.base import Base
from app.models.classroom import Classroom
from app.models.teaching_assignment import TeachingAssignment
from app.models.content import Subject
from app.models.enrollment import Enrollment
from app.models.enums import UserRole
from app.models.school import School
from app.models.user import User


TEST_DATABASE_NAME = "mwalimu_ai_test"

TEST_DATABASE_URL = make_url(
    settings.database_url
).set(
    database=TEST_DATABASE_NAME,
)


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

        await session.rollback()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(
        app=app,
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_users(
    db_session: AsyncSession,
):
    school = School(
        name="Test Secondary School",
        code="TEST-001",
        is_active=True,
    )

    db_session.add(school)
    await db_session.flush()

    teacher = User(
        school_id=school.id,
        login_id="teacher.test",
        full_name="Test Teacher",
        role=UserRole.TEACHER,
        password_hash=hash_password(
            "Teacher123!"
        ),
        is_active=True,
    )

    student = User(
        school_id=school.id,
        login_id="student.test",
        full_name="Test Student",
        role=UserRole.STUDENT,
        password_hash=hash_password(
            "Student123!"
        ),
        is_active=True,
    )

    admin = User(
        school_id=school.id,
        login_id="admin.test",
        full_name="Test School Admin",
        role=UserRole.ADMIN,
        password_hash=hash_password(
            "Admin123!"
        ),
        is_active=True,
    )

    db_session.add_all(
        [
            teacher,
            student,
            admin,
        ]
    )

    await db_session.flush()

    classroom = Classroom(
        school_id=school.id,
        name="Form 2 Test",
        form_level=2,
        academic_year=2026,
    )

    subject = Subject(
        school_id=school.id,
        name="Test Subject",
        slug="test-subject",
        description="Shared subject for test fixtures.",
        is_active=True,
    )

    db_session.add_all(
        [
            classroom,
            subject,
        ]
    )
    await db_session.flush()

    teaching_assignment = TeachingAssignment(
        school_id=school.id,
        teacher_id=teacher.id,
        subject_id=subject.id,
        classroom_id=classroom.id,
        is_active=True,
    )

    db_session.add(teaching_assignment)
    await db_session.flush()

    enrollment = Enrollment(
        classroom_id=classroom.id,
        student_id=student.id,
        is_active=True,
    )

    db_session.add(enrollment)

    await db_session.commit()

    return {
        "school": school,
        "teacher": teacher,
        "student": student,
        "admin": admin,
        "classroom": classroom,
        "subject": subject,
        "teaching_assignment": teaching_assignment,
        "enrollment": enrollment,
    }
