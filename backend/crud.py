from sqlalchemy.orm import Session
from backend import models, schemas


def create_interview(db: Session, interview: schemas.InterviewCreate) -> models.Interview:
    db_interview = models.Interview(**interview.model_dump())
    db.add(db_interview)
    db.commit()
    db.refresh(db_interview)
    return db_interview


def get_interview(db: Session, interview_id: int):
    return db.query(models.Interview).filter(models.Interview.interview_id == interview_id).first()


def get_interviews(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Interview).offset(skip).limit(limit).all()


def set_interview_files(db: Session, interview_id: int, jd_path: str | None, syllabus_path: str | None):
    db_interview = get_interview(db, interview_id)
    if not db_interview:
        return None
    if jd_path:
        db_interview.jd_file_path = jd_path
    if syllabus_path:
        db_interview.syllabus_file_path = syllabus_path
    db.commit()
    db.refresh(db_interview)
    return db_interview


def create_question(db: Session, interview_id: int, question_text: str, topic: str, difficulty: str, question_order: int) -> models.Question:
    db_question = models.Question(
        interview_id=interview_id,
        question_text=question_text,
        topic=topic,
        difficulty=difficulty,
        question_order=question_order,
    )
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question


def get_question(db: Session, question_id: int):
    return db.query(models.Question).filter(models.Question.question_id == question_id).first()


def get_questions_for_interview(db: Session, interview_id: int):
    return (
        db.query(models.Question)
        .filter(models.Question.interview_id == interview_id)
        .order_by(models.Question.question_order)
        .all()
    )


def create_answer(db: Session, question_id: int, answer_text: str, time_taken_seconds: int | None) -> models.Answer:
    db_answer = models.Answer(
        question_id=question_id,
        answer_text=answer_text,
        time_taken_seconds=time_taken_seconds,
    )
    db.add(db_answer)
    db.commit()
    db.refresh(db_answer)
    return db_answer


def create_evaluation(db: Session, answer_id: int, eval_result: dict) -> models.Evaluation:
    db_eval = models.Evaluation(
        answer_id=answer_id,
        score=eval_result.get("score"),
        knowledge_level=eval_result.get("knowledge_level"),
        confidence=eval_result.get("confidence"),
        missing_concepts=eval_result.get("missing_concepts"),
        feedback=eval_result.get("feedback"),
        next_difficulty=eval_result.get("next_difficulty"),
    )
    db.add(db_eval)
    db.commit()
    db.refresh(db_eval)
    return db_eval