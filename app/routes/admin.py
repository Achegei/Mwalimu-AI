import csv
import io

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from openpyxl import load_workbook
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.admin import (
    AdminBulkImportResponse,
    AdminClassroomCreate,
    AdminClassroomSummary,
    AdminEnrollmentStudent,
    AdminUserCreate,
    AdminUserSummary,
)
from app.services.admin_users import (
    bulk_import_school_students,
    create_school_classroom,
    create_school_user,
    enroll_school_student,
    get_school_classroom_students,
    get_school_classrooms,
    get_school_users,
)


router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


@router.get(
    "/users",
    response_model=list[AdminUserSummary],
)
async def list_school_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    ),
) -> list[AdminUserSummary]:
    users = await get_school_users(
        db=db,
        school_id=current_user.school_id,
    )

    return users


@router.post(
    "/users",
    response_model=AdminUserSummary,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    payload: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    ),
) -> AdminUserSummary:
    try:
        user = await create_school_user(
            db=db,
            school_id=current_user.school_id,
            login_id=payload.login_id,
            full_name=payload.full_name,
            role=payload.role,
            password=payload.password,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return user


@router.get(
    "/classrooms",
    response_model=list[AdminClassroomSummary],
)
async def list_school_classrooms(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    ),
) -> list[AdminClassroomSummary]:
    classrooms = await get_school_classrooms(
        db=db,
        school_id=current_user.school_id,
    )

    return classrooms


@router.post(
    "/classrooms",
    response_model=AdminClassroomSummary,
    status_code=status.HTTP_201_CREATED,
)
async def create_classroom(
    payload: AdminClassroomCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    ),
) -> AdminClassroomSummary:
    try:
        classroom = await create_school_classroom(
            db=db,
            school_id=current_user.school_id,
            name=payload.name,
            form_level=payload.form_level,
            academic_year=payload.academic_year,
            teacher_id=payload.teacher_id,
        )
    except ValueError as exc:
        detail = str(exc)

        if "already exists" in detail:
            status_code = status.HTTP_409_CONFLICT
        else:
            status_code = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=status_code,
            detail=detail,
        )

    return classroom


@router.get(
    "/classrooms/{classroom_id}/students",
    response_model=list[AdminEnrollmentStudent],
)
async def list_classroom_students(
    classroom_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    ),
) -> list[AdminEnrollmentStudent]:
    try:
        students = await get_school_classroom_students(
            db=db,
            school_id=current_user.school_id,
            classroom_id=classroom_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    return [
        AdminEnrollmentStudent(**student)
        for student in students
    ]


async def _parse_student_import(
    file: UploadFile,
) -> list[dict[str, str]]:
    filename = (file.filename or "").lower()
    content = await file.read()

    required_columns = {
        "full_name",
        "login_id",
        "password",
    }

    if filename.endswith(".csv"):
        try:
            decoded = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError(
                "CSV file must use UTF-8 encoding."
            ) from exc

        reader = csv.DictReader(
            io.StringIO(decoded)
        )

        fieldnames = {
            str(name).strip()
            for name in (reader.fieldnames or [])
            if name is not None
        }

        if not required_columns.issubset(
            fieldnames
        ):
            raise ValueError(
                "Import file must contain full_name, "
                "login_id, and password columns."
            )

        return [
            {
                str(key).strip(): (
                    "" if value is None else str(value)
                )
                for key, value in row.items()
                if key is not None
            }
            for row in reader
        ]

    if filename.endswith(".xlsx"):
        try:
            workbook = load_workbook(
                io.BytesIO(content),
                read_only=True,
                data_only=True,
            )
        except Exception as exc:
            raise ValueError(
                "Unable to read Excel file."
            ) from exc

        try:
            worksheet = workbook.active
            values = worksheet.iter_rows(
                values_only=True
            )

            header_row = next(values, None)

            if header_row is None:
                raise ValueError(
                    "Import file is empty."
                )

            headers = [
                str(value).strip()
                if value is not None
                else ""
                for value in header_row
            ]

            if not required_columns.issubset(
                set(headers)
            ):
                raise ValueError(
                    "Import file must contain full_name, "
                    "login_id, and password columns."
                )

            rows: list[dict[str, str]] = []

            for values_row in values:
                row = {
                    header: (
                        ""
                        if value is None
                        else str(value)
                    )
                    for header, value in zip(
                        headers,
                        values_row,
                        strict=False,
                    )
                    if header
                }

                rows.append(row)

            return rows
        finally:
            workbook.close()

    raise ValueError(
        "Unsupported file type. Upload a CSV or XLSX file."
    )


@router.post(
    "/classrooms/{classroom_id}/students/import",
    response_model=AdminBulkImportResponse,
)
async def import_classroom_students(
    classroom_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    ),
) -> AdminBulkImportResponse:
    try:
        rows = await _parse_student_import(file)

        result = await bulk_import_school_students(
            db=db,
            school_id=current_user.school_id,
            classroom_id=classroom_id,
            rows=rows,
        )

    except ValueError as exc:
        detail = str(exc)

        if "Classroom not found" in detail:
            status_code = status.HTTP_404_NOT_FOUND
        else:
            status_code = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=status_code,
            detail=detail,
        )

    return AdminBulkImportResponse(**result)


@router.post(
    "/classrooms/{classroom_id}/students/{student_id}",
    response_model=AdminEnrollmentStudent,
    status_code=status.HTTP_201_CREATED,
)
async def enroll_student(
    classroom_id: int,
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    ),
) -> AdminEnrollmentStudent:
    try:
        student = await enroll_school_student(
            db=db,
            school_id=current_user.school_id,
            classroom_id=classroom_id,
            student_id=student_id,
        )
    except ValueError as exc:
        detail = str(exc)

        if "already enrolled" in detail:
            status_code = status.HTTP_409_CONFLICT
        else:
            status_code = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=status_code,
            detail=detail,
        )

    return AdminEnrollmentStudent(**student)

