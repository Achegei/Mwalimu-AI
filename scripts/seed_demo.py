import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.classroom import Classroom
from app.models.enrollment import Enrollment
from app.models.enums import UserRole
from app.models.school import School
from app.models.user import User


DEMO_SCHOOL_CODE = "DEMO-001"

DEMO_TEACHER_LOGIN = "teacher.demo"
DEMO_TEACHER_PASSWORD = "Teacher123!"

DEMO_STUDENT_LOGIN = "student.demo"
DEMO_STUDENT_PASSWORD = "Student123!"


async def get_or_create_school(db) -> School:
    result = await db.execute(select(School).where(School.code == DEMO_SCHOOL_CODE))
    school = result.scalar_one_or_none()

    if school is not None:
        return school

    school = School(
        name="Mwalimu AI Demo Secondary School",
        code=DEMO_SCHOOL_CODE,
        is_active=True,
    )

    db.add(school)
    await db.flush()

    return school


async def get_or_create_teacher(
    db,
    school: School,
) -> User:
    result = await db.execute(select(User).where(User.login_id == DEMO_TEACHER_LOGIN))
    teacher = result.scalar_one_or_none()

    if teacher is not None:
        return teacher

    teacher = User(
        school_id=school.id,
        login_id=DEMO_TEACHER_LOGIN,
        full_name="Demo Biology Teacher",
        role=UserRole.TEACHER,
        password_hash=hash_password(DEMO_TEACHER_PASSWORD),
        is_active=True,
    )

    db.add(teacher)
    await db.flush()

    return teacher


async def get_or_create_student(
    db,
    school: School,
) -> User:
    result = await db.execute(select(User).where(User.login_id == DEMO_STUDENT_LOGIN))
    student = result.scalar_one_or_none()

    if student is not None:
        return student

    student = User(
        school_id=school.id,
        login_id=DEMO_STUDENT_LOGIN,
        full_name="Demo Form 2 Student",
        role=UserRole.STUDENT,
        password_hash=hash_password(DEMO_STUDENT_PASSWORD),
        is_active=True,
    )

    db.add(student)
    await db.flush()

    return student


async def get_or_create_classroom(
    db,
    school: School,
    teacher: User,
) -> Classroom:
    result = await db.execute(
        select(Classroom).where(
            Classroom.school_id == school.id,
            Classroom.name == "Form 2 Demo",
            Classroom.academic_year == 2026,
        )
    )
    classroom = result.scalar_one_or_none()

    if classroom is not None:
        return classroom

    classroom = Classroom(
        school_id=school.id,
        teacher_id=teacher.id,
        name="Form 2 Demo",
        form_level=2,
        academic_year=2026,
    )

    db.add(classroom)
    await db.flush()

    return classroom


async def get_or_create_enrollment(
    db,
    classroom: Classroom,
    student: User,
) -> Enrollment:
    result = await db.execute(
        select(Enrollment).where(
            Enrollment.classroom_id == classroom.id,
            Enrollment.student_id == student.id,
        )
    )
    enrollment = result.scalar_one_or_none()

    if enrollment is not None:
        return enrollment

    enrollment = Enrollment(
        classroom_id=classroom.id,
        student_id=student.id,
        is_active=True,
    )

    db.add(enrollment)
    await db.flush()

    return enrollment


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        try:
            school = await get_or_create_school(db)

            teacher = await get_or_create_teacher(
                db,
                school,
            )

            student = await get_or_create_student(
                db,
                school,
            )

            classroom = await get_or_create_classroom(
                db,
                school,
                teacher,
            )

            await get_or_create_enrollment(
                db,
                classroom,
                student,
            )

            await db.commit()

            print("Demo data seeded successfully.")
            print()
            print("Teacher login:")
            print(f"  login_id: {DEMO_TEACHER_LOGIN}")
            print(f"  password: {DEMO_TEACHER_PASSWORD}")
            print()
            print("Student login:")
            print(f"  login_id: {DEMO_STUDENT_LOGIN}")
            print(f"  password: {DEMO_STUDENT_PASSWORD}")

        except Exception:
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed())
