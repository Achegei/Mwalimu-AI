from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Subject, Topic


async def get_active_subjects(
    db: AsyncSession,
) -> list[Subject]:
    result = await db.execute(
        select(Subject).where(Subject.is_active.is_(True)).order_by(Subject.name.asc())
    )

    return list(result.scalars().all())


async def get_active_topics_for_subject(
    db: AsyncSession,
    subject_id: int,
    form_level: int = 2,
) -> list[Topic]:
    result = await db.execute(
        select(Topic)
        .where(
            Topic.subject_id == subject_id,
            Topic.form_level == form_level,
            Topic.is_active.is_(True),
        )
        .order_by(
            Topic.order_index.asc(),
            Topic.id.asc(),
        )
    )

    return list(result.scalars().all())
