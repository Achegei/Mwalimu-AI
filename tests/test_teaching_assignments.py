import pytest

from app.core.security import hash_password
from app.models.classroom import Classroom
from app.models.content import Subject
from app.models.enums import UserRole
from app.models.school import School
from app.models.user import User
from app.services.teaching_assignments import (
    create_teaching_assignment,
    deactivate_teaching_assignment,
    get_school_teaching_assignments,
)


async def create_school(
    db_session,
    *,
    name: str,
    code: str,
) -> School:
    school = School(
        name=name,
        code=code,
        is_active=True,
    )

    db_session.add(school)
    await db_session.flush()

    return school


async def create_teacher(
    db_session,
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

    db_session.add(teacher)
    await db_session.flush()

    return teacher


async def create_subject(
    db_session,
    *,
    school_id: int,
    name: str,
    slug: str,
) -> Subject:
    subject = Subject(
        school_id=school_id,
        name=name,
        slug=slug,
        description=f"{name} curriculum.",
        is_active=True,
    )

    db_session.add(subject)
    await db_session.flush()

    return subject


async def create_classroom(
    db_session,
    *,
    school_id: int,
    name: str,
    form_level: int,
    academic_year: int = 2026,
) -> Classroom:
    classroom = Classroom(
        school_id=school_id,
        name=name,
        form_level=form_level,
        academic_year=academic_year,
    )

    db_session.add(classroom)
    await db_session.flush()

    return classroom


@pytest.mark.asyncio
async def test_teacher_can_have_multiple_teaching_assignments(
    db_session,
):
    school = await create_school(
        db_session,
        name="Assignment School",
        code="TA-001",
    )

    teacher = await create_teacher(
        db_session,
        school_id=school.id,
        login_id="teacher.multi",
        full_name="Multi Subject Teacher",
    )

    biology = await create_subject(
        db_session,
        school_id=school.id,
        name="Biology",
        slug="ta-biology",
    )

    chemistry = await create_subject(
        db_session,
        school_id=school.id,
        name="Chemistry",
        slug="ta-chemistry",
    )

    form_one = await create_classroom(
        db_session,
        school_id=school.id,
        name="Form 1 East",
        form_level=1,
    )

    form_two = await create_classroom(
        db_session,
        school_id=school.id,
        name="Form 2 East",
        form_level=2,
    )

    first = await create_teaching_assignment(
        db_session,
        school_id=school.id,
        teacher_id=teacher.id,
        subject_id=biology.id,
        classroom_id=form_one.id,
    )

    second = await create_teaching_assignment(
        db_session,
        school_id=school.id,
        teacher_id=teacher.id,
        subject_id=biology.id,
        classroom_id=form_two.id,
    )

    third = await create_teaching_assignment(
        db_session,
        school_id=school.id,
        teacher_id=teacher.id,
        subject_id=chemistry.id,
        classroom_id=form_two.id,
    )

    assert first.teacher_id == teacher.id
    assert second.teacher_id == teacher.id
    assert third.teacher_id == teacher.id

    assignments = await get_school_teaching_assignments(
        db_session,
        school.id,
    )

    assert len(assignments) == 3


@pytest.mark.asyncio
async def test_duplicate_active_teaching_assignment_is_rejected(
    db_session,
):
    school = await create_school(
        db_session,
        name="Duplicate School",
        code="TA-002",
    )

    teacher = await create_teacher(
        db_session,
        school_id=school.id,
        login_id="teacher.duplicate",
        full_name="Duplicate Teacher",
    )

    subject = await create_subject(
        db_session,
        school_id=school.id,
        name="Biology",
        slug="ta-duplicate-biology",
    )

    classroom = await create_classroom(
        db_session,
        school_id=school.id,
        name="Form 2 North",
        form_level=2,
    )

    await create_teaching_assignment(
        db_session,
        school_id=school.id,
        teacher_id=teacher.id,
        subject_id=subject.id,
        classroom_id=classroom.id,
    )

    with pytest.raises(
        ValueError,
        match="already assigned",
    ):
        await create_teaching_assignment(
            db_session,
            school_id=school.id,
            teacher_id=teacher.id,
            subject_id=subject.id,
            classroom_id=classroom.id,
        )


@pytest.mark.asyncio
async def test_assignment_rejects_teacher_from_other_school(
    db_session,
):
    school = await create_school(
        db_session,
        name="Local School",
        code="TA-003",
    )

    foreign_school = await create_school(
        db_session,
        name="Foreign School",
        code="TA-004",
    )

    foreign_teacher = await create_teacher(
        db_session,
        school_id=foreign_school.id,
        login_id="teacher.foreign",
        full_name="Foreign Teacher",
    )

    subject = await create_subject(
        db_session,
        school_id=school.id,
        name="Biology",
        slug="ta-local-biology",
    )

    classroom = await create_classroom(
        db_session,
        school_id=school.id,
        name="Form 3 East",
        form_level=3,
    )

    with pytest.raises(
        ValueError,
        match="Active teacher not found",
    ):
        await create_teaching_assignment(
            db_session,
            school_id=school.id,
            teacher_id=foreign_teacher.id,
            subject_id=subject.id,
            classroom_id=classroom.id,
        )


@pytest.mark.asyncio
async def test_assignment_rejects_subject_from_other_school(
    db_session,
):
    school = await create_school(
        db_session,
        name="Subject Local School",
        code="TA-005",
    )

    foreign_school = await create_school(
        db_session,
        name="Subject Foreign School",
        code="TA-006",
    )

    teacher = await create_teacher(
        db_session,
        school_id=school.id,
        login_id="teacher.subject.scope",
        full_name="Subject Scope Teacher",
    )

    foreign_subject = await create_subject(
        db_session,
        school_id=foreign_school.id,
        name="Foreign Biology",
        slug="ta-foreign-biology",
    )

    classroom = await create_classroom(
        db_session,
        school_id=school.id,
        name="Form 2 West",
        form_level=2,
    )

    with pytest.raises(
        ValueError,
        match="Active subject not found",
    ):
        await create_teaching_assignment(
            db_session,
            school_id=school.id,
            teacher_id=teacher.id,
            subject_id=foreign_subject.id,
            classroom_id=classroom.id,
        )


@pytest.mark.asyncio
async def test_assignment_rejects_classroom_from_other_school(
    db_session,
):
    school = await create_school(
        db_session,
        name="Classroom Local School",
        code="TA-007",
    )

    foreign_school = await create_school(
        db_session,
        name="Classroom Foreign School",
        code="TA-008",
    )

    teacher = await create_teacher(
        db_session,
        school_id=school.id,
        login_id="teacher.classroom.scope",
        full_name="Classroom Scope Teacher",
    )

    subject = await create_subject(
        db_session,
        school_id=school.id,
        name="Biology",
        slug="ta-classroom-biology",
    )

    foreign_classroom = await create_classroom(
        db_session,
        school_id=foreign_school.id,
        name="Form 4 Foreign",
        form_level=4,
    )

    with pytest.raises(
        ValueError,
        match="Classroom not found",
    ):
        await create_teaching_assignment(
            db_session,
            school_id=school.id,
            teacher_id=teacher.id,
            subject_id=subject.id,
            classroom_id=foreign_classroom.id,
        )


@pytest.mark.asyncio
async def test_school_lists_only_its_own_teaching_assignments(
    db_session,
):
    school_a = await create_school(
        db_session,
        name="School A",
        code="TA-009",
    )

    school_b = await create_school(
        db_session,
        name="School B",
        code="TA-010",
    )

    teacher_a = await create_teacher(
        db_session,
        school_id=school_a.id,
        login_id="teacher.school.a",
        full_name="Teacher A",
    )

    teacher_b = await create_teacher(
        db_session,
        school_id=school_b.id,
        login_id="teacher.school.b",
        full_name="Teacher B",
    )

    subject_a = await create_subject(
        db_session,
        school_id=school_a.id,
        name="Biology",
        slug="ta-school-a-biology",
    )

    subject_b = await create_subject(
        db_session,
        school_id=school_b.id,
        name="Biology",
        slug="ta-school-b-biology",
    )

    classroom_a = await create_classroom(
        db_session,
        school_id=school_a.id,
        name="Form 2 A",
        form_level=2,
    )

    classroom_b = await create_classroom(
        db_session,
        school_id=school_b.id,
        name="Form 2 B",
        form_level=2,
    )

    assignment_a = await create_teaching_assignment(
        db_session,
        school_id=school_a.id,
        teacher_id=teacher_a.id,
        subject_id=subject_a.id,
        classroom_id=classroom_a.id,
    )

    await create_teaching_assignment(
        db_session,
        school_id=school_b.id,
        teacher_id=teacher_b.id,
        subject_id=subject_b.id,
        classroom_id=classroom_b.id,
    )

    assignments = await get_school_teaching_assignments(
        db_session,
        school_a.id,
    )

    assert len(assignments) == 1
    assert assignments[0].id == assignment_a.id
    assert assignments[0].school_id == school_a.id


@pytest.mark.asyncio
async def test_teaching_assignment_can_be_deactivated(
    db_session,
):
    school = await create_school(
        db_session,
        name="Deactivate School",
        code="TA-011",
    )

    teacher = await create_teacher(
        db_session,
        school_id=school.id,
        login_id="teacher.deactivate",
        full_name="Deactivate Teacher",
    )

    subject = await create_subject(
        db_session,
        school_id=school.id,
        name="Biology",
        slug="ta-deactivate-biology",
    )

    classroom = await create_classroom(
        db_session,
        school_id=school.id,
        name="Form 1 South",
        form_level=1,
    )

    assignment = await create_teaching_assignment(
        db_session,
        school_id=school.id,
        teacher_id=teacher.id,
        subject_id=subject.id,
        classroom_id=classroom.id,
    )

    deactivated = await deactivate_teaching_assignment(
        db_session,
        school_id=school.id,
        assignment_id=assignment.id,
    )

    assert deactivated.is_active is False


@pytest.mark.asyncio
async def test_inactive_teaching_assignment_can_be_reactivated(
    db_session,
):
    school = await create_school(
        db_session,
        name="Reactivate School",
        code="TA-012",
    )

    teacher = await create_teacher(
        db_session,
        school_id=school.id,
        login_id="teacher.reactivate",
        full_name="Reactivate Teacher",
    )

    subject = await create_subject(
        db_session,
        school_id=school.id,
        name="Biology",
        slug="ta-reactivate-biology",
    )

    classroom = await create_classroom(
        db_session,
        school_id=school.id,
        name="Form 3 South",
        form_level=3,
    )

    assignment = await create_teaching_assignment(
        db_session,
        school_id=school.id,
        teacher_id=teacher.id,
        subject_id=subject.id,
        classroom_id=classroom.id,
    )

    await deactivate_teaching_assignment(
        db_session,
        school_id=school.id,
        assignment_id=assignment.id,
    )

    reactivated = await create_teaching_assignment(
        db_session,
        school_id=school.id,
        teacher_id=teacher.id,
        subject_id=subject.id,
        classroom_id=classroom.id,
    )

    assert reactivated.id == assignment.id
    assert reactivated.is_active is True


@pytest.mark.asyncio
async def test_other_school_cannot_deactivate_assignment(
    db_session,
):
    school = await create_school(
        db_session,
        name="Owner School",
        code="TA-013",
    )

    other_school = await create_school(
        db_session,
        name="Other School",
        code="TA-014",
    )

    teacher = await create_teacher(
        db_session,
        school_id=school.id,
        login_id="teacher.owner",
        full_name="Owner Teacher",
    )

    subject = await create_subject(
        db_session,
        school_id=school.id,
        name="Biology",
        slug="ta-owner-biology",
    )

    classroom = await create_classroom(
        db_session,
        school_id=school.id,
        name="Form 4 Owner",
        form_level=4,
    )

    assignment = await create_teaching_assignment(
        db_session,
        school_id=school.id,
        teacher_id=teacher.id,
        subject_id=subject.id,
        classroom_id=classroom.id,
    )

    with pytest.raises(
        ValueError,
        match="not found in this school",
    ):
        await deactivate_teaching_assignment(
            db_session,
            school_id=other_school.id,
            assignment_id=assignment.id,
        )


async def _login_for_assignment_api(
    client,
    login_id: str,
    password: str,
) -> dict[str, str]:
    response = await client.post(
        "/auth/login",
        json={
            "login_id": login_id,
            "password": password,
        },
    )

    assert response.status_code == 200

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }


async def _create_api_assignment_resources(
    db_session,
    seeded_users,
    *,
    subject_name: str,
    subject_slug: str,
):
    school = seeded_users["school"]
    teacher = seeded_users["teacher"]
    classroom = seeded_users["classroom"]

    subject = await create_subject(
        db_session,
        school_id=school.id,
        name=subject_name,
        slug=subject_slug,
    )

    return teacher, subject, classroom


@pytest.mark.asyncio
async def test_admin_can_create_teaching_assignment_via_api(
    client,
    db_session,
    seeded_users,
):
    headers = await _login_for_assignment_api(
        client,
        "admin.test",
        "Admin123!",
    )

    teacher, subject, classroom = (
        await _create_api_assignment_resources(
            db_session,
            seeded_users,
            subject_name="API Biology",
            subject_slug="ta-api-create-biology",
        )
    )

    response = await client.post(
        "/admin/teaching-assignments",
        headers=headers,
        json={
            "teacher_id": teacher.id,
            "subject_id": subject.id,
            "classroom_id": classroom.id,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["school_id"] == seeded_users["school"].id
    assert data["teacher_id"] == teacher.id
    assert data["subject_id"] == subject.id
    assert data["classroom_id"] == classroom.id
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_admin_can_list_teaching_assignments_via_api(
    client,
    db_session,
    seeded_users,
):
    headers = await _login_for_assignment_api(
        client,
        "admin.test",
        "Admin123!",
    )

    teacher, subject, classroom = (
        await _create_api_assignment_resources(
            db_session,
            seeded_users,
            subject_name="API Listing Biology",
            subject_slug="ta-api-list-biology",
        )
    )

    create_response = await client.post(
        "/admin/teaching-assignments",
        headers=headers,
        json={
            "teacher_id": teacher.id,
            "subject_id": subject.id,
            "classroom_id": classroom.id,
        },
    )

    assert create_response.status_code == 201

    assignment_id = create_response.json()["id"]

    response = await client.get(
        "/admin/teaching-assignments",
        headers=headers,
    )

    assert response.status_code == 200

    assignments = response.json()

    assert any(
        item["id"] == assignment_id
        for item in assignments
    )


@pytest.mark.asyncio
async def test_admin_can_deactivate_teaching_assignment_via_api(
    client,
    db_session,
    seeded_users,
):
    headers = await _login_for_assignment_api(
        client,
        "admin.test",
        "Admin123!",
    )

    teacher, subject, classroom = (
        await _create_api_assignment_resources(
            db_session,
            seeded_users,
            subject_name="API Deactivate Biology",
            subject_slug="ta-api-deactivate-biology",
        )
    )

    create_response = await client.post(
        "/admin/teaching-assignments",
        headers=headers,
        json={
            "teacher_id": teacher.id,
            "subject_id": subject.id,
            "classroom_id": classroom.id,
        },
    )

    assert create_response.status_code == 201

    assignment_id = create_response.json()["id"]

    response = await client.delete(
        f"/admin/teaching-assignments/{assignment_id}",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == assignment_id
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_teacher_cannot_manage_teaching_assignments_via_api(
    client,
    seeded_users,
):
    headers = await _login_for_assignment_api(
        client,
        "teacher.test",
        "Teacher123!",
    )

    response = await client.get(
        "/admin/teaching-assignments",
        headers=headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_student_cannot_manage_teaching_assignments_via_api(
    client,
    seeded_users,
):
    headers = await _login_for_assignment_api(
        client,
        "student.test",
        "Student123!",
    )

    response = await client.get(
        "/admin/teaching-assignments",
        headers=headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_manage_teaching_assignments_via_api(
    client,
):
    response = await client.get(
        "/admin/teaching-assignments",
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_cannot_assign_foreign_teacher_via_api(
    client,
    db_session,
    seeded_users,
):
    headers = await _login_for_assignment_api(
        client,
        "admin.test",
        "Admin123!",
    )

    local_school = seeded_users["school"]
    local_classroom = seeded_users["classroom"]

    local_subject = await create_subject(
        db_session,
        school_id=local_school.id,
        name="Tenant Biology",
        slug="ta-api-foreign-teacher-biology",
    )

    foreign_school = await create_school(
        db_session,
        name="Foreign Teacher API School",
        code="TA-API-FOREIGN-TEACHER",
    )

    foreign_teacher = await create_teacher(
        db_session,
        school_id=foreign_school.id,
        login_id="teacher.api.foreign",
        full_name="Foreign API Teacher",
    )

    response = await client.post(
        "/admin/teaching-assignments",
        headers=headers,
        json={
            "teacher_id": foreign_teacher.id,
            "subject_id": local_subject.id,
            "classroom_id": local_classroom.id,
        },
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Active teacher not found in this school."
    )


@pytest.mark.asyncio
async def test_admin_cannot_assign_foreign_subject_via_api(
    client,
    db_session,
    seeded_users,
):
    headers = await _login_for_assignment_api(
        client,
        "admin.test",
        "Admin123!",
    )

    local_teacher = seeded_users["teacher"]
    local_classroom = seeded_users["classroom"]

    foreign_school = await create_school(
        db_session,
        name="Foreign Subject API School",
        code="TA-API-FOREIGN-SUBJECT",
    )

    foreign_subject = await create_subject(
        db_session,
        school_id=foreign_school.id,
        name="Foreign API Biology",
        slug="ta-api-foreign-subject-biology",
    )

    response = await client.post(
        "/admin/teaching-assignments",
        headers=headers,
        json={
            "teacher_id": local_teacher.id,
            "subject_id": foreign_subject.id,
            "classroom_id": local_classroom.id,
        },
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Active subject not found in this school."
    )


@pytest.mark.asyncio
async def test_admin_cannot_assign_foreign_classroom_via_api(
    client,
    db_session,
    seeded_users,
):
    headers = await _login_for_assignment_api(
        client,
        "admin.test",
        "Admin123!",
    )

    local_school = seeded_users["school"]
    local_teacher = seeded_users["teacher"]

    local_subject = await create_subject(
        db_session,
        school_id=local_school.id,
        name="Classroom Boundary Biology",
        slug="ta-api-foreign-classroom-biology",
    )

    foreign_school = await create_school(
        db_session,
        name="Foreign Classroom API School",
        code="TA-API-FOREIGN-CLASSROOM",
    )

    foreign_classroom = await create_classroom(
        db_session,
        school_id=foreign_school.id,
        name="Form 2 Foreign API",
        form_level=2,
    )

    response = await client.post(
        "/admin/teaching-assignments",
        headers=headers,
        json={
            "teacher_id": local_teacher.id,
            "subject_id": local_subject.id,
            "classroom_id": foreign_classroom.id,
        },
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Classroom not found in this school."
    )


@pytest.mark.asyncio
async def test_teacher_can_get_own_active_teaching_assignment(
    db_session,
):
    school = await create_school(
        db_session,
        name="Teacher Assignment School",
        code="TA-019",
    )

    teacher = await create_teacher(
        db_session,
        school_id=school.id,
        login_id="teacher.assignment.owner",
        full_name="Assignment Owner",
    )

    subject = await create_subject(
        db_session,
        school_id=school.id,
        name="Biology",
        slug="ta-owner-biology",
    )

    classroom = await create_classroom(
        db_session,
        school_id=school.id,
        name="Form 2 East",
        form_level=2,
    )

    assignment = await create_teaching_assignment(
        db_session,
        school_id=school.id,
        teacher_id=teacher.id,
        subject_id=subject.id,
        classroom_id=classroom.id,
    )

    from app.services.teaching_assignments import (
        get_teacher_teaching_assignment,
    )

    result = await get_teacher_teaching_assignment(
        db_session,
        teacher_id=teacher.id,
        school_id=school.id,
        assignment_id=assignment.id,
    )

    assert result is not None
    assert result.id == assignment.id
    assert result.teacher_id == teacher.id
    assert result.subject_id == subject.id
    assert result.classroom_id == classroom.id


@pytest.mark.asyncio
async def test_teacher_cannot_get_another_teachers_assignment(
    db_session,
):
    school = await create_school(
        db_session,
        name="Teacher Isolation School",
        code="TA-020",
    )

    owner = await create_teacher(
        db_session,
        school_id=school.id,
        login_id="teacher.assignment.owner.two",
        full_name="Assignment Owner Two",
    )

    other_teacher = await create_teacher(
        db_session,
        school_id=school.id,
        login_id="teacher.assignment.other",
        full_name="Other Teacher",
    )

    subject = await create_subject(
        db_session,
        school_id=school.id,
        name="Chemistry",
        slug="ta-isolation-chemistry",
    )

    classroom = await create_classroom(
        db_session,
        school_id=school.id,
        name="Form 3 East",
        form_level=3,
    )

    assignment = await create_teaching_assignment(
        db_session,
        school_id=school.id,
        teacher_id=owner.id,
        subject_id=subject.id,
        classroom_id=classroom.id,
    )

    from app.services.teaching_assignments import (
        get_teacher_teaching_assignment,
    )

    result = await get_teacher_teaching_assignment(
        db_session,
        teacher_id=other_teacher.id,
        school_id=school.id,
        assignment_id=assignment.id,
    )

    assert result is None


@pytest.mark.asyncio
async def test_teacher_assignment_lookup_enforces_school_boundary(
    db_session,
):
    school = await create_school(
        db_session,
        name="Assignment Local School",
        code="TA-021",
    )

    other_school = await create_school(
        db_session,
        name="Assignment Foreign School",
        code="TA-022",
    )

    teacher = await create_teacher(
        db_session,
        school_id=school.id,
        login_id="teacher.assignment.school",
        full_name="School Boundary Teacher",
    )

    subject = await create_subject(
        db_session,
        school_id=school.id,
        name="Physics",
        slug="ta-boundary-physics",
    )

    classroom = await create_classroom(
        db_session,
        school_id=school.id,
        name="Form 4 East",
        form_level=4,
    )

    assignment = await create_teaching_assignment(
        db_session,
        school_id=school.id,
        teacher_id=teacher.id,
        subject_id=subject.id,
        classroom_id=classroom.id,
    )

    from app.services.teaching_assignments import (
        get_teacher_teaching_assignment,
    )

    result = await get_teacher_teaching_assignment(
        db_session,
        teacher_id=teacher.id,
        school_id=other_school.id,
        assignment_id=assignment.id,
    )

    assert result is None


@pytest.mark.asyncio
async def test_inactive_assignment_is_not_available_to_teacher(
    db_session,
):
    school = await create_school(
        db_session,
        name="Inactive Assignment School",
        code="TA-023",
    )

    teacher = await create_teacher(
        db_session,
        school_id=school.id,
        login_id="teacher.assignment.inactive",
        full_name="Inactive Assignment Teacher",
    )

    subject = await create_subject(
        db_session,
        school_id=school.id,
        name="Geography",
        slug="ta-inactive-geography",
    )

    classroom = await create_classroom(
        db_session,
        school_id=school.id,
        name="Form 2 North",
        form_level=2,
    )

    assignment = await create_teaching_assignment(
        db_session,
        school_id=school.id,
        teacher_id=teacher.id,
        subject_id=subject.id,
        classroom_id=classroom.id,
    )

    await deactivate_teaching_assignment(
        db_session,
        school_id=school.id,
        assignment_id=assignment.id,
    )

    from app.services.teaching_assignments import (
        get_teacher_teaching_assignment,
    )

    result = await get_teacher_teaching_assignment(
        db_session,
        teacher_id=teacher.id,
        school_id=school.id,
        assignment_id=assignment.id,
    )

    assert result is None


@pytest.mark.asyncio
async def test_teacher_lists_only_own_active_teaching_assignments(
    db_session,
):
    school = await create_school(
        db_session,
        name="Teacher Assignment List School",
        code="TA-024",
    )

    teacher = await create_teacher(
        db_session,
        school_id=school.id,
        login_id="teacher.assignment.list",
        full_name="Assignment List Teacher",
    )

    other_teacher = await create_teacher(
        db_session,
        school_id=school.id,
        login_id="teacher.assignment.list.other",
        full_name="Other Assignment Teacher",
    )

    biology = await create_subject(
        db_session,
        school_id=school.id,
        name="Biology",
        slug="ta-list-biology",
    )

    chemistry = await create_subject(
        db_session,
        school_id=school.id,
        name="Chemistry",
        slug="ta-list-chemistry",
    )

    classroom = await create_classroom(
        db_session,
        school_id=school.id,
        name="Form 2 South",
        form_level=2,
    )

    active_assignment = await create_teaching_assignment(
        db_session,
        school_id=school.id,
        teacher_id=teacher.id,
        subject_id=biology.id,
        classroom_id=classroom.id,
    )

    inactive_assignment = await create_teaching_assignment(
        db_session,
        school_id=school.id,
        teacher_id=teacher.id,
        subject_id=chemistry.id,
        classroom_id=classroom.id,
    )

    await create_teaching_assignment(
        db_session,
        school_id=school.id,
        teacher_id=other_teacher.id,
        subject_id=biology.id,
        classroom_id=classroom.id,
    )

    await deactivate_teaching_assignment(
        db_session,
        school_id=school.id,
        assignment_id=inactive_assignment.id,
    )

    from app.services.teaching_assignments import (
        get_teacher_teaching_assignments,
    )

    assignments = await get_teacher_teaching_assignments(
        db_session,
        teacher_id=teacher.id,
        school_id=school.id,
    )

    assert len(assignments) == 1
    assert assignments[0].id == active_assignment.id
    assert assignments[0].teacher_id == teacher.id
    assert assignments[0].is_active is True
