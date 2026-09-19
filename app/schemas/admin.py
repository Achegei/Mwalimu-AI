from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import UserRole


class AdminUserSummary(BaseModel):
    id: int
    school_id: int
    login_id: str
    full_name: str
    role: UserRole
    is_active: bool

    model_config = {
        "from_attributes": True,
    }


class AdminUserCreate(BaseModel):
    login_id: str = Field(
        min_length=3,
        max_length=100,
    )
    full_name: str = Field(
        min_length=1,
        max_length=200,
    )
    role: Literal[
        UserRole.TEACHER,
        UserRole.STUDENT,
    ]
    password: str = Field(
        min_length=6,
        max_length=128,
    )


class AdminClassroomSummary(BaseModel):
    id: int
    school_id: int
    teacher_id: int | None
    name: str
    form_level: int
    academic_year: int

    model_config = {
        "from_attributes": True,
    }


class AdminClassroomCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )
    form_level: int = Field(
        ge=1,
        le=4,
    )
    academic_year: int = Field(
        ge=2000,
        le=2100,
    )
    teacher_id: int | None = None


class AdminEnrollmentStudent(BaseModel):
    student_id: int
    login_id: str
    full_name: str
    is_active: bool


class AdminBulkImportRow(BaseModel):
    row_number: int
    login_id: str
    status: Literal[
        "enrolled",
        "skipped",
        "failed",
    ]
    message: str


class AdminBulkImportResponse(BaseModel):
    total_rows: int
    created: int
    enrolled: int
    skipped: int
    failed: int
    rows: list[AdminBulkImportRow]

