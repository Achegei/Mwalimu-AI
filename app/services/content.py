from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Subject, Topic


async def get_active_subjects(
    db: AsyncSession,
    school_id: int,
) -> list[Subject]:
    """
    Return active subjects owned by the authenticated user's school.
    """

    result = await db.execute(
        select(Subject)
        .where(
            Subject.school_id == school_id,
            Subject.is_active.is_(True),
        )
        .order_by(Subject.name.asc())
    )

    return list(result.scalars().all())


async def get_active_topics_for_subject(
    db: AsyncSession,
    subject_id: int,
    school_id: int,
    form_level: int = 2,
) -> list[Topic]:
    """
    Return active topics only when their subject belongs to the
    authenticated user's school.
    """

    result = await db.execute(
        select(Topic)
        .join(
            Subject,
            Topic.subject_id == Subject.id,
        )
        .where(
            Topic.subject_id == subject_id,
            Subject.school_id == school_id,
            Subject.is_active.is_(True),
            Topic.form_level == form_level,
            Topic.is_active.is_(True),
        )
        .order_by(
            Topic.order_index.asc(),
            Topic.id.asc(),
        )
    )

    return list(result.scalars().all())


async def get_active_topic_for_school(
    db: AsyncSession,
    topic_id: int,
    school_id: int,
) -> Topic | None:
    """
    Return an active topic only when its active subject belongs to
    the authenticated user's school.
    """

    result = await db.execute(
        select(Topic)
        .join(
            Subject,
            Topic.subject_id == Subject.id,
        )
        .where(
            Topic.id == topic_id,
            Topic.is_active.is_(True),
            Subject.school_id == school_id,
            Subject.is_active.is_(True),
        )
    )

    return result.scalar_one_or_none()
