from app.models.enums import (
    DocumentProcessingStatus,
    DocumentScope,
    DocumentType,
)
from app.schemas.content import StudentProgressResponse
from pydantic import BaseModel


class TeacherClassSummary(BaseModel):
    id: int
    name: str
    form_level: int
    academic_year: int
    school_id: int

    model_config = {
        "from_attributes": True,
    }


class TeacherClassLearningSummary(BaseModel):
    classroom_id: int
    classroom_name: str
    form_level: int
    academic_year: int

    student_count: int

    completed_diagnostics: int
    completed_practice_attempts: int

    average_diagnostic_score: float | None
    average_practice_score: float | None


class TeacherTopicPerformance(BaseModel):
    topic_id: int
    topic_title: str
    topic_slug: str

    students_assessed: int

    completed_diagnostics: int
    completed_practice_attempts: int

    average_diagnostic_score: float | None
    average_practice_score: float | None
    improvement_percentage_points: float | None


class TeacherClassTopicPerformanceResponse(BaseModel):
    classroom_id: int
    classroom_name: str
    topics: list[TeacherTopicPerformance]


class TeacherWeakTopic(BaseModel):
    topic_id: int
    topic_title: str
    topic_slug: str

    students_assessed: int
    completed_diagnostics: int
    completed_practice_attempts: int

    average_diagnostic_score: float | None
    average_practice_score: float | None
    improvement_percentage_points: float | None

    weakness_status: str
    is_weak: bool


class TeacherWeakTopicsResponse(BaseModel):
    classroom_id: int
    classroom_name: str

    weak_topic_count: int
    assessed_topic_count: int
    insufficient_data_topic_count: int

    weakest_topic_id: int | None
    weakest_topic_title: str | None

    topics: list[TeacherWeakTopic]


class TeacherInsightTopicContext(BaseModel):
    topic_id: int
    topic_title: str
    topic_slug: str

    weakness_status: str

    students_assessed: int
    completed_diagnostics: int
    completed_practice_attempts: int

    average_diagnostic_score: float | None
    average_practice_score: float | None
    improvement_percentage_points: float | None


class TeacherInsightEvidence(BaseModel):
    student_count: int
    assessed_topic_count: int
    weak_topic_count: int
    insufficient_data_topic_count: int


class TeacherInsightContext(BaseModel):
    classroom_id: int
    classroom_name: str
    form_level: int
    academic_year: int

    evidence: TeacherInsightEvidence

    weakest_topic: TeacherInsightTopicContext | None


class TeacherGeneratedInsight(BaseModel):
    teacher_summary: str
    main_learning_concern: str
    suggested_intervention: str
    follow_up_recommendation: str


class TeacherInsightResponse(BaseModel):
    context: TeacherInsightContext
    insight: TeacherGeneratedInsight


class TeacherClassStudent(BaseModel):
    student_id: int
    full_name: str
    login_id: str


class TeacherStudentProgressStudent(BaseModel):
    student_id: int
    full_name: str
    login_id: str


class TeacherStudentProgressResponse(BaseModel):
    classroom_id: int
    classroom_name: str
    student: TeacherStudentProgressStudent
    progress: StudentProgressResponse


class TeacherDocumentSummary(BaseModel):
    id: int
    school_id: int
    subject_id: int
    topic_id: int | None
    scope: DocumentScope
    teaching_assignment_id: int
    uploaded_by_id: int | None
    title: str
    document_type: DocumentType
    form_level: int
    academic_year: int | None
    exam_year: int | None
    paper_number: str | None
    original_filename: str
    storage_key: str
    mime_type: str
    file_size: int
    processing_status: DocumentProcessingStatus
    error_message: str | None
    is_active: bool

    model_config = {
        "from_attributes": True,
    }
