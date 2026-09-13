from datetime import datetime

from pydantic import BaseModel


class TopicSummary(BaseModel):
    id: int
    slug: str
    title: str
    summary: str | None
    form_level: int
    order_index: int

    model_config = {
        "from_attributes": True,
    }


class SubjectSummary(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None

    model_config = {
        "from_attributes": True,
    }


class SubjectWithTopics(SubjectSummary):
    topics: list[TopicSummary]


class DiagnosticQuestion(BaseModel):
    id: int
    question_type: str
    difficulty: str
    prompt: str
    options: list | None
    marks: int

    model_config = {
        "from_attributes": True,
    }


class DiagnosticStartResponse(BaseModel):
    attempt_id: int
    topic_id: int
    topic_title: str
    assessment_type: str
    status: str
    total_questions: int
    questions: list[DiagnosticQuestion]


class DiagnosticAnswerRequest(BaseModel):
    question_id: int
    answer: str


class DiagnosticAnswerResponse(BaseModel):
    attempt_id: int
    question_id: int
    submitted_answer: str
    is_correct: bool
    marks_awarded: int
    explanation: str | None


class DiagnosticResultResponse(BaseModel):
    attempt_id: int
    topic_id: int
    correct_answers: int
    total_questions: int
    score_percentage: float
    status: str


class DiagnosticInterpretationResponse(BaseModel):
    attempt_id: int
    topic_id: int
    score_percentage: float
    performance_level: str
    weak_questions: list[int]
    weak_difficulties: list[str]
    recommended_action: str


class TutorStartResponse(BaseModel):
    attempt_id: int
    topic_id: int
    message: str


class TutorMessageRequest(BaseModel):
    message: str


class TutorMessageResponse(BaseModel):
    attempt_id: int
    topic_id: int
    student_message: str
    tutor_message: str


class PracticeQuestion(BaseModel):
    id: int
    question_type: str
    difficulty: str
    prompt: str
    options: list | None
    marks: int

    model_config = {
        "from_attributes": True,
    }


class PracticeStartResponse(BaseModel):
    attempt_id: int
    diagnostic_attempt_id: int
    topic_id: int
    topic_title: str
    assessment_type: str
    status: str
    total_questions: int
    questions: list[PracticeQuestion]


class PracticeAnswerRequest(BaseModel):
    question_id: int
    submitted_answer: str


class PracticeAnswerResponse(BaseModel):
    attempt_id: int
    question_id: int
    submitted_answer: str
    is_correct: bool
    marks_awarded: int


class PracticeCompleteResponse(BaseModel):
    attempt_id: int
    assessment_type: str
    status: str
    correct_answers: int
    total_questions: int
    score_percentage: float
    completed_at: datetime


class LearningImprovementResponse(BaseModel):
    diagnostic_attempt_id: int
    practice_attempt_id: int
    topic_id: int

    diagnostic_score: float
    practice_score: float
    improvement_percentage_points: float

    improved: bool
    learning_status: str

    message: str
    recommended_action: str


class StudentTopicProgress(BaseModel):
    subject_id: int
    subject_name: str

    topic_id: int
    topic_title: str

    diagnostic_attempt_id: int
    diagnostic_score: float

    practice_attempt_id: int | None
    practice_score: float | None

    improvement_percentage_points: float | None
    learning_status: str

    completed_at: datetime


class StudentProgressResponse(BaseModel):
    completed_topics: int
    improved_topics: int
    unchanged_topics: int
    declined_topics: int

    topics: list[StudentTopicProgress]
