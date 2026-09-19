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

