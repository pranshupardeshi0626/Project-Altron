from datetime import datetime
from pydantic import BaseModel


class InterviewCreate(BaseModel):
    title: str
    role: str
    experience_level: str
    duration_minutes: int
    total_questions: int


class InterviewOut(BaseModel):
    interview_id: int
    title: str
    role: str
    experience_level: str
    duration_minutes: int
    total_questions: int
    jd_file_path: str | None = None
    syllabus_file_path: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class QuestionOut(BaseModel):
    question_id: int
    interview_id: int
    question_text: str
    topic: str | None = None
    difficulty: str | None = None
    question_order: int
    created_at: datetime

    class Config:
        from_attributes = True


class AnswerSubmit(BaseModel):
    question_id: int
    answer_text: str
    time_taken_seconds: int | None = None


class EvaluationOut(BaseModel):
    evaluation_id: int
    answer_id: int
    score: float | None = None
    knowledge_level: str | None = None
    confidence: str | None = None
    missing_concepts: str | None = None
    feedback: str | None = None
    next_difficulty: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True