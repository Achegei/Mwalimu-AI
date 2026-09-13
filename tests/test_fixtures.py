import pytest
from sqlalchemy import select

from app.models.user import User


@pytest.mark.asyncio
async def test_seeded_users_exist(
    db_session,
    seeded_users,
):
    result = await db_session.execute(
        select(User).order_by(User.id)
    )

    users = result.scalars().all()

    assert len(users) == 2
    assert users[0].login_id == "teacher.test"
    assert users[1].login_id == "student.test"
