from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import AssessmentAttempt
from app.models.classroom import Classroom
from app.models.content import Topic
from app.models.enrollment import Enrollment
from app.models.enums import (
    AssessmentStatus,
    AssessmentType,
)


async def get_teacher_classes(
    db: AsyncSession,
    teacher_id: int,
) -> list[Classroom]:
    result = await db.execute(
        select(Classroom)
        .where(
            Classroom.teacher_id == teacher_id,
        )
        .order_by(
            Classroom.academic_year.desc(),
            Classroom.form_level.asc(),
            Classroom.name.asc(),
        )
    )

    return list(result.scalars().all())


async def get_teacher_classroom(
    db: AsyncSession,
    teacher_id: int,
    teacher_school_id: int,
    classroom_id: int,
) -> Classroom | None:
    result = await db.execute(
        select(Classroom).where(
            Classroom.id == classroom_id,
            Classroom.teacher_id == teacher_id,
            Classroom.school_id == teacher_school_id,
        )
    )

    return result.scalar_one_or_none()


async def get_class_learning_summary(
    db: AsyncSession,
    teacher_id: int,
    teacher_school_id: int,
    classroom_id: int,
) -> dict:
    classroom = await get_teacher_classroom(
        db=db,
        teacher_id=teacher_id,
        teacher_school_id=teacher_school_id,
        classroom_id=classroom_id,
    )

    if classroom is None:
        raise ValueError("Classroom not found.")

    student_count_result = await db.execute(
        select(func.count(Enrollment.id)).where(
            Enrollment.classroom_id == classroom.id,
            Enrollment.is_active.is_(True),
        )
    )

    student_count = student_count_result.scalar_one()

    diagnostic_result = await db.execute(
        select(
            func.count(AssessmentAttempt.id),
            func.avg(AssessmentAttempt.score_percentage),
        ).where(
            AssessmentAttempt.classroom_id == classroom.id,
            AssessmentAttempt.assessment_type == AssessmentType.DIAGNOSTIC,
            AssessmentAttempt.status == AssessmentStatus.COMPLETED,
        )
    )

    diagnostic_count, diagnostic_average = diagnostic_result.one()

    practice_result = await db.execute(
        select(
            func.count(AssessmentAttempt.id),
            func.avg(AssessmentAttempt.score_percentage),
        ).where(
            AssessmentAttempt.classroom_id == classroom.id,
            AssessmentAttempt.assessment_type == AssessmentType.PRACTICE,
            AssessmentAttempt.status == AssessmentStatus.COMPLETED,
        )
    )

    practice_count, practice_average = practice_result.one()

    return {
        "classroom_id": classroom.id,
        "classroom_name": classroom.name,
        "form_level": classroom.form_level,
        "academic_year": classroom.academic_year,
        "student_count": student_count,
        "completed_diagnostics": diagnostic_count,
        "completed_practice_attempts": practice_count,
        "average_diagnostic_score": (
            round(float(diagnostic_average), 2)
            if diagnostic_average is not None
            else None
        ),
        "average_practice_score": (
            round(float(practice_average), 2) if practice_average is not None else None
        ),
    }


async def get_class_topic_performance(
    db: AsyncSession,
    teacher_id: int,
    teacher_school_id: int,
    classroom_id: int,
) -> dict:
    classroom = await get_teacher_classroom(
        db=db,
        teacher_id=teacher_id,
        teacher_school_id=teacher_school_id,
        classroom_id=classroom_id,
    )

    if classroom is None:
        raise ValueError("Classroom not found.")

    topics_result = await db.execute(
        select(Topic)
        .where(
            Topic.form_level == classroom.form_level,
        )
        .order_by(
            Topic.order_index.asc(),
            Topic.id.asc(),
        )
    )

    topics = list(topics_result.scalars().all())

    topic_results = []

    for topic in topics:
        students_assessed_result = await db.execute(
            select(func.count(distinct(AssessmentAttempt.student_id))).where(
                AssessmentAttempt.classroom_id == classroom.id,
                AssessmentAttempt.topic_id == topic.id,
                AssessmentAttempt.status == AssessmentStatus.COMPLETED,
            )
        )

        students_assessed = students_assessed_result.scalar_one()

        diagnostic_result = await db.execute(
            select(
                func.count(AssessmentAttempt.id),
                func.avg(AssessmentAttempt.score_percentage),
            ).where(
                AssessmentAttempt.classroom_id == classroom.id,
                AssessmentAttempt.topic_id == topic.id,
                AssessmentAttempt.assessment_type == AssessmentType.DIAGNOSTIC,
                AssessmentAttempt.status == AssessmentStatus.COMPLETED,
            )
        )

        diagnostic_count, diagnostic_average = diagnostic_result.one()

        practice_result = await db.execute(
            select(
                func.count(AssessmentAttempt.id),
                func.avg(AssessmentAttempt.score_percentage),
            ).where(
                AssessmentAttempt.classroom_id == classroom.id,
                AssessmentAttempt.topic_id == topic.id,
                AssessmentAttempt.assessment_type == AssessmentType.PRACTICE,
                AssessmentAttempt.status == AssessmentStatus.COMPLETED,
            )
        )

        practice_count, practice_average = practice_result.one()

        diagnostic_score = (
            round(float(diagnostic_average), 2)
            if diagnostic_average is not None
            else None
        )

        practice_score = (
            round(float(practice_average), 2) if practice_average is not None else None
        )

        improvement = None

        if diagnostic_score is not None and practice_score is not None:
            improvement = round(
                practice_score - diagnostic_score,
                2,
            )

        topic_results.append(
            {
                "topic_id": topic.id,
                "topic_title": topic.title,
                "topic_slug": topic.slug,
                "students_assessed": students_assessed,
                "completed_diagnostics": diagnostic_count,
                "completed_practice_attempts": practice_count,
                "average_diagnostic_score": diagnostic_score,
                "average_practice_score": practice_score,
                "improvement_percentage_points": improvement,
            }
        )

    return {
        "classroom_id": classroom.id,
        "classroom_name": classroom.name,
        "topics": topic_results,
    }


async def identify_class_weak_topics(
    db: AsyncSession,
    teacher_id: int,
    teacher_school_id: int,
    classroom_id: int,
) -> dict:
    performance = await get_class_topic_performance(
        db=db,
        teacher_id=teacher_id,
        teacher_school_id=teacher_school_id,
        classroom_id=classroom_id,
    )

    classified_topics = []

    weak_topic_count = 0
    assessed_topic_count = 0
    insufficient_data_topic_count = 0

    weakest_topic = None

    for topic in performance["topics"]:
        diagnostic_score = topic["average_diagnostic_score"]

        if diagnostic_score is None:
            weakness_status = "insufficient_data"
            is_weak = False
            insufficient_data_topic_count += 1

        elif diagnostic_score < 50:
            weakness_status = "critical"
            is_weak = True
            weak_topic_count += 1
            assessed_topic_count += 1

        elif diagnostic_score < 70:
            weakness_status = "needs_attention"
            is_weak = True
            weak_topic_count += 1
            assessed_topic_count += 1

        else:
            weakness_status = "satisfactory"
            is_weak = False
            assessed_topic_count += 1

        classified_topic = {
            **topic,
            "weakness_status": weakness_status,
            "is_weak": is_weak,
        }

        classified_topics.append(classified_topic)

        if diagnostic_score is not None and (
            weakest_topic is None
            or diagnostic_score < weakest_topic["average_diagnostic_score"]
        ):
            weakest_topic = classified_topic

    classified_topics.sort(
        key=lambda item: (
            item["average_diagnostic_score"] is None,
            (
                item["average_diagnostic_score"]
                if item["average_diagnostic_score"] is not None
                else 101
            ),
            item["topic_id"],
        )
    )

    return {
        "classroom_id": performance["classroom_id"],
        "classroom_name": performance["classroom_name"],
        "weak_topic_count": weak_topic_count,
        "assessed_topic_count": assessed_topic_count,
        "insufficient_data_topic_count": insufficient_data_topic_count,
        "weakest_topic_id": (
            weakest_topic["topic_id"] if weakest_topic is not None else None
        ),
        "weakest_topic_title": (
            weakest_topic["topic_title"] if weakest_topic is not None else None
        ),
        "topics": classified_topics,
    }


async def build_teacher_insight_context(
    db: AsyncSession,
    teacher_id: int,
    teacher_school_id: int,
    classroom_id: int,
) -> dict:
    class_summary = await get_class_learning_summary(
        db=db,
        teacher_id=teacher_id,
        teacher_school_id=teacher_school_id,
        classroom_id=classroom_id,
    )

    weak_topic_analysis = await identify_class_weak_topics(
        db=db,
        teacher_id=teacher_id,
        teacher_school_id=teacher_school_id,
        classroom_id=classroom_id,
    )

    weakest_topic = None

    weakest_topic_id = weak_topic_analysis["weakest_topic_id"]

    if weakest_topic_id is not None:
        matching_topic = next(
            (
                topic
                for topic in weak_topic_analysis["topics"]
                if topic["topic_id"] == weakest_topic_id
            ),
            None,
        )

        if matching_topic is not None:
            weakest_topic = {
                "topic_id": matching_topic["topic_id"],
                "topic_title": matching_topic["topic_title"],
                "topic_slug": matching_topic["topic_slug"],
                "weakness_status": matching_topic["weakness_status"],
                "students_assessed": matching_topic["students_assessed"],
                "completed_diagnostics": matching_topic["completed_diagnostics"],
                "completed_practice_attempts": matching_topic[
                    "completed_practice_attempts"
                ],
                "average_diagnostic_score": matching_topic["average_diagnostic_score"],
                "average_practice_score": matching_topic["average_practice_score"],
                "improvement_percentage_points": matching_topic[
                    "improvement_percentage_points"
                ],
            }

    return {
        "classroom_id": class_summary["classroom_id"],
        "classroom_name": class_summary["classroom_name"],
        "form_level": class_summary["form_level"],
        "academic_year": class_summary["academic_year"],
        "evidence": {
            "student_count": class_summary["student_count"],
            "assessed_topic_count": weak_topic_analysis["assessed_topic_count"],
            "weak_topic_count": weak_topic_analysis["weak_topic_count"],
            "insufficient_data_topic_count": weak_topic_analysis[
                "insufficient_data_topic_count"
            ],
        },
        "weakest_topic": weakest_topic,
    }
