from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import AuthenticatedUser, LoginRequest, LoginResponse
from app.services.auth import authenticate_user

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/login",
    response_model=LoginResponse,
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    user = await authenticate_user(
        db=db,
        login_id=payload.login_id,
        password=payload.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login credentials.",
        )

    access_token = create_access_token(
        subject=str(user.id),
        additional_claims={
            "role": user.role.value,
            "school_id": user.school_id,
        },
    )

    return LoginResponse(
        access_token=access_token,
        user=user,
    )


@router.get(
    "/me",
    response_model=AuthenticatedUser,
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> AuthenticatedUser:
    return current_user
