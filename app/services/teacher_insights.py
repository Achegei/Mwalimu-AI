import json

from openai import AsyncOpenAI

from app.core.config import settings
from app.schemas.teacher import (
    TeacherGeneratedInsight,
    TeacherInsightContext,
)


TEACHER_INSIGHT_SYSTEM_PROMPT = """
You are an AI teaching assistant supporting a secondary-school teacher.

Your job is to interpret structured classroom learning analytics and produce
a concise, practical teacher insight.

You must follow these rules:

1. Use only the analytics provided in the teacher insight context.
2. Do not invent students, scores, topics, causes, observations, or trends.
3. Clearly distinguish evidence from interpretation.
4. Acknowledge when the available evidence is limited.
5. Never describe class-level aggregate analytics as an individual student's
   performance.
6. Never write claims such as "the student scored", "the student improved",
   "the student achieved", or equivalent individual-level claims.
7. Do not treat aggregate diagnostic-to-practice score differences as paired
   student improvement unless the supplied data explicitly proves that.
8. Do not diagnose learning disabilities, medical conditions, or personal
   characteristics.
9. Do not claim that an unassessed topic is weak.
10. Treat topics marked "insufficient_data" as unassessed or insufficiently
    evidenced, not as weak.
11. Recommendations must be practical, educational, and directly related to
    the supplied topic evidence.
12. Do not change, recalculate, or override supplied scores or weakness
    classifications.
13. If the evidence is too limited for a strong conclusion, say so explicitly.
14. When student_count is less than 2, do not recommend group-based,
    peer-group, or small-group interventions.
15. When evidence is based on only one assessed topic, do not generalize the
    result to the entire curriculum or overall learner ability.
16. Describe diagnostic and practice differences as aggregate score
    differences, not proven individual improvement.
17. When insufficient_data_topic_count is greater than 0, explicitly state
    that assessment coverage is limited and that some topics have insufficient
    data.

Produce exactly these four fields:

- teacher_summary
- main_learning_concern
- suggested_intervention
- follow_up_recommendation

Keep every field concise and suitable for a teacher dashboard.
""".strip()


def build_teacher_insight_prompt(
    context: TeacherInsightContext,
) -> str:
    context_json = json.dumps(
        context.model_dump(),
        indent=2,
    )

    return f"""
Analyze the following verified classroom learning analytics.

VERIFIED TEACHER INSIGHT CONTEXT:

{context_json}

Important interpretation rules:

- Base every factual statement only on the supplied context.
- Preserve the supplied weakness classification.
- Refer to the results as class-level or assessed-classroom evidence.
- Never convert class aggregates into claims about an individual student.
- Topics with insufficient data must not be classified as strong or weak.
- A higher practice average than diagnostic average may be described as an
  aggregate score increase or as evidence suggesting improvement.
- Do not claim that an individual learner improved unless paired evidence is
  explicitly supplied.
- If student_count is less than 2, recommend an individual review activity,
  targeted reteaching, guided practice, or another appropriate intervention,
  not group instruction.
- Give one intervention focused on the weakest evidenced topic.
- Give one follow-up action that either checks progress or gathers stronger
  evidence.
- If insufficient_data_topic_count is greater than 0, the teacher_summary
  must explicitly acknowledge that assessment coverage is limited and that
  some topics have insufficient data.
""".strip()


def ensure_assessment_coverage_acknowledgement(
    insight: TeacherGeneratedInsight,
    context: TeacherInsightContext,
) -> TeacherGeneratedInsight:
    if context.evidence.insufficient_data_topic_count <= 0:
        return insight

    combined_text = " ".join(
        [
            insight.teacher_summary,
            insight.main_learning_concern,
            insight.suggested_intervention,
            insight.follow_up_recommendation,
        ]
    ).lower()

    evidence_limit_terms = (
        "limited",
        "insufficient",
        "unassessed",
        "not assessed",
        "coverage",
    )

    if any(
        term in combined_text
        for term in evidence_limit_terms
    ):
        return insight

    assessed_count = context.evidence.assessed_topic_count
    insufficient_count = (
        context.evidence.insufficient_data_topic_count
    )

    coverage_statement = (
        "Assessment coverage is limited: "
        f"{assessed_count} topic(s) have assessment evidence, "
        f"while {insufficient_count} topic(s) have insufficient data."
    )

    updated_summary = (
        f"{insight.teacher_summary.rstrip()} "
        f"{coverage_statement}"
    )

    return insight.model_copy(
        update={
            "teacher_summary": updated_summary,
        }
    )


def validate_teacher_insight(
    insight: TeacherGeneratedInsight,
    context: TeacherInsightContext,
) -> TeacherGeneratedInsight:
    fields = {
        "teacher_summary": insight.teacher_summary,
        "main_learning_concern": insight.main_learning_concern,
        "suggested_intervention": insight.suggested_intervention,
        "follow_up_recommendation": insight.follow_up_recommendation,
    }

    for field_name, value in fields.items():
        if not value.strip():
            raise RuntimeError(
                f"Teacher insight field '{field_name}' is empty."
            )

    combined_text = " ".join(
        value.lower()
        for value in fields.values()
    )

    forbidden_individual_claims = (
        "the student scored",
        "the student achieved",
        "the student improved",
        "the student's score",
        "the learner scored",
        "the learner achieved",
        "the learner improved",
        "the learner's score",
    )

    for phrase in forbidden_individual_claims:
        if phrase in combined_text:
            raise RuntimeError(
                "Teacher insight contains an unsupported "
                f"individual-level claim: '{phrase}'."
            )

    if context.evidence.student_count < 2:
        forbidden_group_recommendations = (
            "small-group",
            "small group",
            "group instruction",
            "group-based",
            "peer group",
            "peer-group",
        )

        intervention = (
            insight.suggested_intervention.lower()
        )

        for phrase in forbidden_group_recommendations:
            if phrase in intervention:
                raise RuntimeError(
                    "Teacher insight recommends a group-based "
                    "intervention despite fewer than 2 students."
                )

    weakest_topic = context.weakest_topic

    if weakest_topic is not None:
        topic_title = weakest_topic.topic_title.lower()

        concern_and_intervention = " ".join(
            [
                insight.main_learning_concern.lower(),
                insight.suggested_intervention.lower(),
            ]
        )

        if topic_title not in concern_and_intervention:
            raise RuntimeError(
                "Teacher insight does not reference the "
                "verified weakest topic."
            )

        if (
            weakest_topic.weakness_status.lower()
            not in combined_text
        ):
            raise RuntimeError(
                "Teacher insight does not preserve the "
                "verified weakness classification."
            )

    if context.evidence.insufficient_data_topic_count > 0:
        evidence_limit_terms = (
            "limited",
            "insufficient",
            "unassessed",
            "not assessed",
            "coverage",
        )

        if not any(
            term in combined_text
            for term in evidence_limit_terms
        ):
            raise RuntimeError(
                "Teacher insight does not acknowledge "
                "limited assessment coverage."
            )

    return insight


async def generate_teacher_insight(
    context: TeacherInsightContext,
) -> TeacherGeneratedInsight:
    if not settings.ai_teacher_insights_enabled:
        raise RuntimeError(
            "AI teacher insights are disabled."
        )

    if not settings.openai_api_key:
        raise RuntimeError(
            "OpenAI API key is not configured."
        )

    if not settings.openai_model:
        raise RuntimeError(
            "OpenAI model is not configured."
        )

    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
    )

    response = await client.responses.parse(
        model=settings.openai_model,
        instructions=TEACHER_INSIGHT_SYSTEM_PROMPT,
        input=build_teacher_insight_prompt(context),
        text_format=TeacherGeneratedInsight,
        temperature=0.2,
    )

    parsed_insight = None

    for output_item in response.output:
        if output_item.type != "message":
            continue

        for content_item in output_item.content:
            if content_item.type != "output_text":
                continue

            if content_item.parsed is not None:
                parsed_insight = content_item.parsed
                break

        if parsed_insight is not None:
            break

    if parsed_insight is None:
        raise RuntimeError(
            "OpenAI did not return a valid structured "
            "teacher insight."
        )

    parsed_insight = ensure_assessment_coverage_acknowledgement(
        insight=parsed_insight,
        context=context,
    )

    return validate_teacher_insight(
        insight=parsed_insight,
        context=context,
    )
