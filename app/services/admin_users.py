from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User


async def get_school_users(
    db: AsyncSession,
    school_id: int,
) -> list[User]:
    """
    Return users belonging only to the authenticated admin's school.
    """

    result = await db.execute(
        select(User)
        .where(
            User.school_id == school_id,
        )
        .order_by(
            User.full_name.asc(),
            User.id.asc(),
        )
    )

    return list(result.scalars().all())


async def create_school_user(
    db: AsyncSession,
    school_id: int,
    login_id: str,
    full_name: str,
    role: UserRole,
    password: str,
) -> User:
    """
    Create a teacher or student owned by the authenticated
    admin's school.
    """

    existing_result = await db.execute(
        select(User.id).where(
            User.login_id == login_id,
        )
    )

    if existing_result.scalar_one_or_none() is not None:
        raise ValueError("A user with this login ID already exists.")

    user = User(
        school_id=school_id,
        login_id=login_id,
        full_name=full_name,
        role=role,
        password_hash=hash_password(password),
        is_active=True,
    )

    db.add(user)

    await db.commit()
    await db.refresh(user)

    return user

