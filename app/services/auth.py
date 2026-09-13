from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.user import User


async def get_user_by_login_id(
    db: AsyncSession,
    login_id: str,
) -> User | None:
    result = await db.execute(select(User).where(User.login_id == login_id))

    return result.scalar_one_or_none()


async def authenticate_user(
    db: AsyncSession,
    login_id: str,
    password: str,
) -> User | None:
    user = await get_user_by_login_id(
        db=db,
        login_id=login_id,
    )

    if user is None:
        return None

    if not user.is_active:
        return None

    if not verify_password(
        plain_password=password,
        hashed_password=user.password_hash,
    ):
        return None

    return user
