from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base


class Interview(Base):
    __tablename__ = "interviews"

    interview_id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    role = Column(String, nullable=False)
    experience_level = Column(String, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    jd_file_path = Column(String, nullable=True)
    syllabus_file_path = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    questions = relationship("Question", back_populates="interview", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    question_id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.interview_id"), nullable=False)
    question_text = Column(Text, nullable=False)
    topic = Column(String, nullable=True)
    difficulty = Column(String, nullable=True)
    question_order = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    interview = relationship("Interview", back_populates="questions")
    answer = relationship("Answer", back_populates="question", uselist=False, cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"

    answer_id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.question_id"), nullable=False)
    answer_text = Column(Text, nullable=False)
    time_taken_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    question = relationship("Question", back_populates="answer")
    evaluation = relationship("Evaluation", back_populates="answer", uselist=False, cascade="all, delete-orphan")


class Evaluation(Base):
    __tablename__ = "evaluations"

    evaluation_id = Column(Integer, primary_key=True, index=True)
    answer_id = Column(Integer, ForeignKey("answers.answer_id"), nullable=False)
    score = Column(Float, nullable=True)
    knowledge_level = Column(String, nullable=True)
    confidence = Column(String, nullable=True)
    missing_concepts = Column(Text, nullable=True)
    feedback = Column(Text, nullable=True)
    next_difficulty = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    answer = relationship("Answer", back_populates="evaluation")