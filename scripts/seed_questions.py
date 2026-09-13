import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.content import Question, Topic
from app.models.enums import DifficultyLevel, QuestionType


QUESTION_BANK = {
    "transport-in-plants-and-animals": [
        {
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": DifficultyLevel.EASY,
            "prompt": "Which tissue transports water and mineral salts in plants?",
            "options": [
                "Phloem",
                "Xylem",
                "Epidermis",
                "Cambium",
            ],
            "correct_answer": "Xylem",
            "explanation": (
                "Xylem transports water and dissolved mineral salts "
                "from the roots to other parts of the plant."
            ),
            "marks": 1,
        },
        {
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": DifficultyLevel.MEDIUM,
            "prompt": "Which component of blood mainly transports oxygen?",
            "options": [
                "Plasma",
                "Platelets",
                "Red blood cells",
                "White blood cells",
            ],
            "correct_answer": "Red blood cells",
            "explanation": (
                "Red blood cells contain haemoglobin, which binds "
                "and transports oxygen."
            ),
            "marks": 1,
        },
        {
            "question_type": QuestionType.TRUE_FALSE,
            "difficulty": DifficultyLevel.MEDIUM,
            "prompt": "Phloem transports manufactured food in plants.",
            "options": [
                "True",
                "False",
            ],
            "correct_answer": "True",
            "explanation": (
                "Phloem transports manufactured food such as sugars "
                "from leaves to other parts of the plant."
            ),
            "marks": 1,
        },
        {
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": DifficultyLevel.EASY,
            "prompt": "Which blood vessels carry blood away from the heart?",
            "options": [
                "Veins",
                "Arteries",
                "Capillaries",
                "Venules",
            ],
            "correct_answer": "Arteries",
            "explanation": (
                "Arteries carry blood away from the heart to other parts of the body."
            ),
            "marks": 1,
        },
        {
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": DifficultyLevel.MEDIUM,
            "prompt": ("Which feature of red blood cells helps them transport oxygen?"),
            "options": [
                "They contain haemoglobin",
                "They contain chlorophyll",
                "They produce antibodies",
                "They form blood clots",
            ],
            "correct_answer": "They contain haemoglobin",
            "explanation": (
                "Haemoglobin in red blood cells binds oxygen and allows "
                "it to be transported efficiently around the body."
            ),
            "marks": 1,
        },
        {
            "question_type": QuestionType.TRUE_FALSE,
            "difficulty": DifficultyLevel.MEDIUM,
            "prompt": "Capillaries have thin walls that allow exchange of substances.",
            "options": [
                "True",
                "False",
            ],
            "correct_answer": "True",
            "explanation": (
                "Capillary walls are very thin, allowing substances such "
                "as oxygen, nutrients, and wastes to move between the "
                "blood and body tissues."
            ),
            "marks": 1,
        },
    ],
    "gaseous-exchange": [
        {
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": DifficultyLevel.EASY,
            "prompt": "Where does gaseous exchange mainly occur in the human lungs?",
            "options": [
                "Trachea",
                "Bronchi",
                "Alveoli",
                "Diaphragm",
            ],
            "correct_answer": "Alveoli",
            "explanation": (
                "Alveoli provide a large, thin, moist surface for "
                "efficient gaseous exchange."
            ),
            "marks": 1,
        },
        {
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": DifficultyLevel.MEDIUM,
            "prompt": "Which gas diffuses from the alveoli into the blood?",
            "options": [
                "Carbon dioxide",
                "Oxygen",
                "Nitrogen",
                "Water vapour",
            ],
            "correct_answer": "Oxygen",
            "explanation": (
                "Oxygen moves from the alveoli into the blood by diffusion."
            ),
            "marks": 1,
        },
        {
            "question_type": QuestionType.TRUE_FALSE,
            "difficulty": DifficultyLevel.MEDIUM,
            "prompt": "Stomata are involved in gaseous exchange in leaves.",
            "options": [
                "True",
                "False",
            ],
            "correct_answer": "True",
            "explanation": (
                "Stomata allow gases such as carbon dioxide and oxygen "
                "to move into and out of leaves."
            ),
            "marks": 1,
        },
        {
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": DifficultyLevel.EASY,
            "prompt": ("Which structure controls the opening and closing of stomata?"),
            "options": [
                "Guard cells",
                "Xylem vessels",
                "Root hairs",
                "Palisade cells",
            ],
            "correct_answer": "Guard cells",
            "explanation": (
                "Guard cells change shape to control whether stomata "
                "are open or closed."
            ),
            "marks": 1,
        },
        {
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": DifficultyLevel.MEDIUM,
            "prompt": ("Why are alveoli well suited for gaseous exchange?"),
            "options": [
                "They have thick walls",
                "They have a small surface area",
                "They have thin walls and a large surface area",
                "They are filled with cartilage",
            ],
            "correct_answer": "They have thin walls and a large surface area",
            "explanation": (
                "Thin walls provide a short diffusion distance, while "
                "the large surface area increases the amount of gas "
                "that can diffuse."
            ),
            "marks": 1,
        },
        {
            "question_type": QuestionType.TRUE_FALSE,
            "difficulty": DifficultyLevel.MEDIUM,
            "prompt": (
                "Carbon dioxide normally diffuses from the blood into the alveoli."
            ),
            "options": [
                "True",
                "False",
            ],
            "correct_answer": "True",
            "explanation": (
                "Carbon dioxide moves from the blood into the alveoli "
                "and is then removed from the body during exhalation."
            ),
            "marks": 1,
        },
    ],
    "respiration": [
        {
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": DifficultyLevel.EASY,
            "prompt": "What is the main purpose of respiration in living cells?",
            "options": [
                "To produce water",
                "To release energy",
                "To absorb oxygen",
                "To remove carbon dioxide",
            ],
            "correct_answer": "To release energy",
            "explanation": (
                "Respiration releases energy from food molecules "
                "for use in cellular activities."
            ),
            "marks": 1,
        },
        {
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": DifficultyLevel.MEDIUM,
            "prompt": "Which substance is broken down during aerobic respiration?",
            "options": [
                "Glucose",
                "Protein",
                "Mineral salts",
                "Vitamins",
            ],
            "correct_answer": "Glucose",
            "explanation": (
                "Glucose is broken down in the presence of oxygen "
                "during aerobic respiration."
            ),
            "marks": 1,
        },
        {
            "question_type": QuestionType.TRUE_FALSE,
            "difficulty": DifficultyLevel.MEDIUM,
            "prompt": "Anaerobic respiration can occur without oxygen.",
            "options": [
                "True",
                "False",
            ],
            "correct_answer": "True",
            "explanation": (
                "Anaerobic respiration releases energy without using oxygen."
            ),
            "marks": 1,
        },
        {
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": DifficultyLevel.EASY,
            "prompt": ("Which gas is required for aerobic respiration?"),
            "options": [
                "Oxygen",
                "Nitrogen",
                "Carbon dioxide",
                "Hydrogen",
            ],
            "correct_answer": "Oxygen",
            "explanation": (
                "Aerobic respiration uses oxygen to release energy from glucose."
            ),
            "marks": 1,
        },
        {
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": DifficultyLevel.MEDIUM,
            "prompt": ("Which products are formed during aerobic respiration?"),
            "options": [
                "Carbon dioxide and water",
                "Oxygen and glucose",
                "Lactic acid only",
                "Glucose and water",
            ],
            "correct_answer": "Carbon dioxide and water",
            "explanation": (
                "During aerobic respiration, glucose reacts with oxygen "
                "and produces carbon dioxide and water while releasing energy."
            ),
            "marks": 1,
        },
        {
            "question_type": QuestionType.TRUE_FALSE,
            "difficulty": DifficultyLevel.MEDIUM,
            "prompt": (
                "Aerobic respiration generally releases more energy "
                "than anaerobic respiration."
            ),
            "options": [
                "True",
                "False",
            ],
            "correct_answer": "True",
            "explanation": (
                "Aerobic respiration releases more energy from glucose "
                "than anaerobic respiration."
            ),
            "marks": 1,
        },
    ],
    "excretion-and-homeostasis": [
        {
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": DifficultyLevel.EASY,
            "prompt": "Which organ mainly removes urea from the blood?",
            "options": [
                "Heart",
                "Kidney",
                "Lung",
                "Pancreas",
            ],
            "correct_answer": "Kidney",
            "explanation": (
                "The kidneys filter the blood and remove urea as part of urine."
            ),
            "marks": 1,
        },
        {
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": DifficultyLevel.MEDIUM,
            "prompt": "What does homeostasis mean?",
            "options": [
                "Removal of undigested food",
                "Maintenance of a stable internal environment",
                "Movement of substances around the body",
                "Production of energy from food",
            ],
            "correct_answer": "Maintenance of a stable internal environment",
            "explanation": (
                "Homeostasis is the regulation of internal conditions "
                "within suitable limits."
            ),
            "marks": 1,
        },
        {
            "question_type": QuestionType.TRUE_FALSE,
            "difficulty": DifficultyLevel.MEDIUM,
            "prompt": "Sweating helps regulate body temperature.",
            "options": [
                "True",
                "False",
            ],
            "correct_answer": "True",
            "explanation": ("Evaporation of sweat from the skin helps cool the body."),
            "marks": 1,
        },
        {
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": DifficultyLevel.EASY,
            "prompt": ("Which organ removes carbon dioxide from the body?"),
            "options": [
                "Lungs",
                "Kidneys",
                "Liver",
                "Skin",
            ],
            "correct_answer": "Lungs",
            "explanation": (
                "The lungs remove carbon dioxide from the blood during exhalation."
            ),
            "marks": 1,
        },
        {
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": DifficultyLevel.MEDIUM,
            "prompt": (
                "What happens to the skin blood vessels when the body "
                "needs to lose more heat?"
            ),
            "options": [
                "They widen",
                "They become completely blocked",
                "They stop carrying blood",
                "They become permanently narrower",
            ],
            "correct_answer": "They widen",
            "explanation": (
                "Widening of blood vessels near the skin increases "
                "blood flow close to the surface, allowing more heat "
                "to be lost."
            ),
            "marks": 1,
        },
        {
            "question_type": QuestionType.TRUE_FALSE,
            "difficulty": DifficultyLevel.MEDIUM,
            "prompt": ("The kidneys help regulate the amount of water in the body."),
            "options": [
                "True",
                "False",
            ],
            "correct_answer": "True",
            "explanation": (
                "The kidneys regulate water balance by changing the "
                "amount of water removed in urine."
            ),
            "marks": 1,
        },
    ],
}


async def get_topic(
    db,
    slug: str,
) -> Topic:
    result = await db.execute(
        select(Topic).where(
            Topic.slug == slug,
            Topic.is_active.is_(True),
        )
    )

    topic = result.scalar_one_or_none()

    if topic is None:
        raise RuntimeError(f"Topic not found: {slug}")

    return topic


async def question_exists(
    db,
    topic_id: int,
    prompt: str,
) -> bool:
    result = await db.execute(
        select(Question.id).where(
            Question.topic_id == topic_id,
            Question.prompt == prompt,
        )
    )

    return result.scalar_one_or_none() is not None


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        try:
            created_count = 0
            existing_count = 0

            for topic_slug, questions in QUESTION_BANK.items():
                topic = await get_topic(
                    db,
                    topic_slug,
                )

                for question_data in questions:
                    exists = await question_exists(
                        db,
                        topic.id,
                        question_data["prompt"],
                    )

                    if exists:
                        existing_count += 1
                        continue

                    question = Question(
                        topic_id=topic.id,
                        question_type=question_data["question_type"],
                        difficulty=question_data["difficulty"],
                        prompt=question_data["prompt"],
                        options=question_data["options"],
                        correct_answer=question_data["correct_answer"],
                        explanation=question_data["explanation"],
                        marks=question_data["marks"],
                        is_active=True,
                    )

                    db.add(question)
                    created_count += 1

            await db.commit()

            print("Biology question bank seeded successfully.")
            print(f"Questions created: {created_count}")
            print(f"Questions already existing: {existing_count}")

        except Exception:
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed())
