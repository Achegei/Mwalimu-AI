import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.content import Subject, Topic
from app.models.school import School


DEMO_SCHOOL_CODE = "DEMO-001"
BIOLOGY_SLUG = "biology"


BIOLOGY_TOPICS = [
    {
        "slug": "transport-in-plants-and-animals",
        "title": "Transport in Plants and Animals",
        "summary": (
            "Movement of substances in plants and animals, including "
            "transport tissues, the circulatory system, and related processes."
        ),
        "form_level": 2,
        "order_index": 1,
    },
    {
        "slug": "gaseous-exchange",
        "title": "Gaseous Exchange",
        "summary": (
            "How organisms exchange respiratory gases and the structures "
            "adapted for gaseous exchange."
        ),
        "form_level": 2,
        "order_index": 2,
    },
    {
        "slug": "respiration",
        "title": "Respiration",
        "summary": (
            "The release of energy from food, including aerobic and "
            "anaerobic respiration."
        ),
        "form_level": 2,
        "order_index": 3,
    },
    {
        "slug": "excretion-and-homeostasis",
        "title": "Excretion and Homeostasis",
        "summary": (
            "Removal of metabolic waste and regulation of internal "
            "conditions in living organisms."
        ),
        "form_level": 2,
        "order_index": 4,
    },
]


async def get_school(db) -> School:
    result = await db.execute(
        select(School).where(
            School.code == DEMO_SCHOOL_CODE,
            School.is_active.is_(True),
        )
    )

    school = result.scalar_one_or_none()

    if school is None:
        raise RuntimeError(
            "Demo school DEMO-001 does not exist. "
            "Run scripts/seed_demo.py before scripts/seed_content.py."
        )

    return school


async def get_or_create_subject(
    db,
    school: School,
) -> Subject:
    result = await db.execute(
        select(Subject).where(
            Subject.school_id == school.id,
            Subject.slug == BIOLOGY_SLUG,
        )
    )

    subject = result.scalar_one_or_none()

    if subject is not None:
        return subject

    subject = Subject(
        school_id=school.id,
        name="Biology",
        slug=BIOLOGY_SLUG,
        description=(
            "Form 2 Biology learning content "
            "for the Mwalimu AI MVP."
        ),
        is_active=True,
    )

    db.add(subject)
    await db.flush()

    return subject


async def get_or_create_topic(
    db,
    subject: Subject,
    topic_data: dict,
) -> Topic:
    result = await db.execute(
        select(Topic).where(
            Topic.subject_id == subject.id,
            Topic.slug == topic_data["slug"],
        )
    )

    topic = result.scalar_one_or_none()

    if topic is not None:
        return topic

    topic = Topic(
        subject_id=subject.id,
        slug=topic_data["slug"],
        title=topic_data["title"],
        summary=topic_data["summary"],
        form_level=topic_data["form_level"],
        order_index=topic_data["order_index"],
        is_active=True,
    )

    db.add(topic)
    await db.flush()

    return topic


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        try:
            school = await get_school(db)

            subject = await get_or_create_subject(
                db,
                school,
            )

            for topic_data in BIOLOGY_TOPICS:
                await get_or_create_topic(
                    db,
                    subject,
                    topic_data,
                )

            await db.commit()

            print("Biology content seeded successfully.")
            print(f"School: {school.name}")
            print(f"Subject: {subject.name}")
            print(f"Topics: {len(BIOLOGY_TOPICS)}")

        except Exception:
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed())
