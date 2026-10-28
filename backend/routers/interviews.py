import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from backend import crud, schemas, rag, question_gen, reports, session_recovery
from backend.database import get_db

router = APIRouter(prefix="/interviews", tags=["interviews"])

UPLOAD_DIR = "documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/", response_model=schemas.InterviewOut)
def create_interview(interview: schemas.InterviewCreate, db: Session = Depends(get_db)):
    return crud.create_interview(db, interview)


@router.get("/", response_model=list[schemas.InterviewOut])
def list_interviews(db: Session = Depends(get_db)):
    return crud.get_interviews(db)


@router.get("/{interview_id}", response_model=schemas.InterviewOut)
def get_interview(interview_id: int, db: Session = Depends(get_db)):
    db_interview = crud.get_interview(db, interview_id)
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return db_interview


@router.post("/{interview_id}/upload")
def upload_documents(
    interview_id: int,
    jd_file: UploadFile | None = File(None),
    syllabus_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    db_interview = crud.get_interview(db, interview_id)
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    interview_dir = os.path.join(UPLOAD_DIR, str(interview_id))
    os.makedirs(interview_dir, exist_ok=True)

    jd_path = None
    syllabus_path = None
    jd_chunks = 0
    syllabus_chunks = 0

    if jd_file is not None:
        jd_path = os.path.join(interview_dir, jd_file.filename)
        with open(jd_path, "wb") as f:
            shutil.copyfileobj(jd_file.file, f)
        jd_chunks = rag.process_document(interview_id, jd_path, "jd")

    if syllabus_file is not None:
        syllabus_path = os.path.join(interview_dir, syllabus_file.filename)
        with open(syllabus_path, "wb") as f:
            shutil.copyfileobj(syllabus_file.file, f)
        syllabus_chunks = rag.process_document(interview_id, syllabus_path, "syllabus")

    updated_interview = crud.set_interview_files(db, interview_id, jd_path, syllabus_path)

    return {
        "interview": schemas.InterviewOut.model_validate(updated_interview),
        "jd_chunks_stored": jd_chunks,
        "syllabus_chunks_stored": syllabus_chunks,
    }


@router.get("/{interview_id}/search")
def search_knowledge_base(interview_id: int, query: str, n_results: int = 5):
    results = rag.query_knowledge_base(interview_id, query, n_results)
    return {"query": query, "results": results}


@router.post("/{interview_id}/generate-questions")
def generate_interview_questions(
    interview_id: int,
    topic: str,
    difficulty: str = "intermediate",
    num_questions: int = 3,
    db: Session = Depends(get_db),
):
    db_interview = crud.get_interview(db, interview_id)
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    questions = question_gen.generate_questions(interview_id, topic, difficulty, num_questions)
    return {"topic": topic, "difficulty": difficulty, "questions": questions}


@router.post("/{interview_id}/start")
def start_interview(interview_id: int, topic: str, db: Session = Depends(get_db)):
    db_interview = crud.get_interview(db, interview_id)
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    if crud.get_questions_for_interview(db, interview_id):
        raise HTTPException(
            status_code=400,
            detail="This interview has already started. Use the resume option to continue it.",
        )

    try:
        questions = question_gen.generate_questions(interview_id, topic, "beginner", num_questions=1)
    except Exception:
        raise HTTPException(status_code=503, detail="AI service is busy. Please try again in a moment.")

    if not questions or questions[0].get("parse_error"):
        raise HTTPException(status_code=500, detail="Failed to generate a valid question")

    q = questions[0]
    db_question = crud.create_question(
        db,
        interview_id=interview_id,
        question_text=q["question"],
        topic=q.get("topic", topic),
        difficulty=q.get("difficulty", "beginner"),
        question_order=1,
    )

    return schemas.QuestionOut.model_validate(db_question)


@router.post("/{interview_id}/submit-answer")
def submit_answer(interview_id: int, submission: schemas.AnswerSubmit, db: Session = Depends(get_db)):
    """
    The answer is saved FIRST. Evaluation and next-question generation happen afterwards,
    and if either fails the answer stays safely in the database for a later retry.
    """
    db_interview = crud.get_interview(db, interview_id)
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    db_question = crud.get_question(db, submission.question_id)
    if not db_question or db_question.interview_id != interview_id:
        raise HTTPException(status_code=404, detail="Question not found for this interview")

    # Step 1: save the answer right away (unless it was already saved by an earlier attempt)
    if db_question.answer is None:
        crud.create_answer(
            db,
            question_id=submission.question_id,
            answer_text=submission.answer_text,
            time_taken_seconds=submission.time_taken_seconds,
        )
        db.refresh(db_question)

    is_last = db_question.question_order >= db_interview.total_questions

    # Step 2: evaluate it
    db_eval = session_recovery.evaluate_saved_answer(db, db_question)
    if db_eval is None:
        return {
            "status": "saved_pending_evaluation",
            "message": "Your answer is saved. The AI service is busy, so it will be evaluated when you resume.",
            "evaluation": None,
            "interview_complete": False,
            "next_question": None,
        }

    evaluation_out = schemas.EvaluationOut.model_validate(db_eval)

    if is_last:
        return {
            "status": "ok",
            "message": "Interview complete.",
            "evaluation": evaluation_out,
            "interview_complete": True,
            "next_question": None,
        }

    # Step 3: create the next question
    next_question = session_recovery.create_next_question(db, db_interview, db_question, db_eval)
    if next_question is None:
        return {
            "status": "saved_pending_next_question",
            "message": "Your answer is saved and evaluated. The next question could not be generated yet, so resume to continue.",
            "evaluation": evaluation_out,
            "interview_complete": False,
            "next_question": None,
        }

    return {
        "status": "ok",
        "message": "",
        "evaluation": evaluation_out,
        "interview_complete": False,
        "next_question": schemas.QuestionOut.model_validate(next_question),
    }


@router.post("/{interview_id}/resume")
def resume_interview(interview_id: int, db: Session = Depends(get_db)):
    """
    Finishes whatever step was interrupted (evaluating a saved answer, creating the
    next question) and returns the full state so the frontend can continue.
    """
    db_interview = crud.get_interview(db, interview_id)
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    questions = crud.get_questions_for_interview(db, interview_id)
    if questions:
        last = questions[-1]
        if last.answer is not None:
            db_eval = session_recovery.evaluate_saved_answer(db, last)
            if db_eval is not None:
                session_recovery.create_next_question(db, db_interview, last, db_eval)

    return session_recovery.build_state(db, db_interview)


@router.get("/{interview_id}/state")
def get_interview_state(interview_id: int, db: Session = Depends(get_db)):
    """Read-only view of where the interview is. Does not call the AI."""
    db_interview = crud.get_interview(db, interview_id)
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    return session_recovery.build_state(db, db_interview)


@router.get("/{interview_id}/report/candidate")
def get_candidate_report(interview_id: int, db: Session = Depends(get_db)):
    db_interview = crud.get_interview(db, interview_id)
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    return reports.generate_candidate_report(db, interview_id)


@router.get("/{interview_id}/report/quality")
def get_interview_quality_report(interview_id: int, db: Session = Depends(get_db)):
    db_interview = crud.get_interview(db, interview_id)
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    return reports.generate_interview_quality_report(db, interview_id)