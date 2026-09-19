from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class AssessmentType(str, Enum):
    DIAGNOSTIC = "diagnostic"
    PRACTICE = "practice"
    POST_LEARNING = "post_learning"


class AssessmentStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class LearningEventType(str, Enum):
    SESSION_STARTED = "session_started"
    TOPIC_SELECTED = "topic_selected"
    DIAGNOSTIC_STARTED = "diagnostic_started"
    QUESTION_ANSWERED = "question_answered"
    TUTOR_INTERACTION = "tutor_interaction"
    PRACTICE_STARTED = "practice_started"
    PRACTICE_COMPLETED = "practice_completed"
    ASSESSMENT_COMPLETED = "assessment_completed"
    SESSION_COMPLETED = "session_completed"
