from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.admin import AdminUserCreate, AdminUserSummary
from app.services.admin_users import (
    create_school_user,
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

