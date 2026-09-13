from pydantic import BaseModel, Field

from app.models.enums import UserRole


class LoginRequest(BaseModel):
    login_id: str = Field(
        min_length=3,
        max_length=100,
    )

    password: str = Field(
        min_length=6,
        max_length=128,
    )


class AuthenticatedUser(BaseModel):
    id: int
    login_id: str
    full_name: str
    role: UserRole
    school_id: int

    model_config = {
        "from_attributes": True,
    }


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthenticatedUser
