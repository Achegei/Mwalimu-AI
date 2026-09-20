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


class DocumentScope(str, Enum):
    COMMON = "common"
    TEACHING_ASSIGNMENT = "teaching_assignment"


class DocumentType(str, Enum):
    CURRICULUM = "curriculum"
    TEXTBOOK = "textbook"
    TEACHER_NOTES = "teacher_notes"
    REFERENCE = "reference"
    REVISION = "revision"
    PAST_PAPER = "past_paper"
    MARKING_SCHEME = "marking_scheme"
    MOCK_EXAM = "mock_exam"
    OTHER = "other"


class DocumentProcessingStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
