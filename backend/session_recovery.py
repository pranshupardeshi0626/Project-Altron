from sqlalchemy.orm import Session
from backend import crud, evaluation, question_gen, models, schemas


def evaluate_saved_answer(db: Session, db_question: models.Question):
    """
    Evaluates an answer that is already saved in the database.
    Returns the evaluation, or None if the AI is unavailable (the answer stays saved).
    """
    db_answer = db_question.answer
    if db_answer is None:
        return None
    if db_answer.evaluation is not None:
        return db_answer.evaluation

    try:
        result = evaluation.evaluate_answer(
            interview_id=db_question.interview_id,
            question_text=db_question.question_text,
            answer_text=db_answer.answer_text,
            current_difficulty=db_question.difficulty or "beginner",
        )
    except Exception:
        return None

    return crud.create_evaluation(db, db_answer.answer_id, result)


def create_next_question(db: Session, db_interview: models.Interview, db_question: models.Question, db_eval):
    """
    Makes sure the question after db_question exists.
    Returns it, or None if the interview is over or the AI is unavailable.
    """
    next_order = db_question.question_order + 1
    if next_order > db_interview.total_questions:
        return None

    existing = crud.get_questions_for_interview(db, db_interview.interview_id)
    for q in existing:
        if q.question_order == next_order:
            return q  # already created earlier, do not duplicate

    next_difficulty = db_eval.next_difficulty or db_question.difficulty or "beginner"
    try:
        questions = question_gen.generate_questions(
            db_interview.interview_id,
            db_question.topic or "general",
            next_difficulty,
            num_questions=1,
            avoid_questions=[q.question_text for q in existing],
        )
    except Exception:
        return None

    if not questions or questions[0].get("parse_error"):
        return None

    nq = questions[0]
    return crud.create_question(
        db,
        interview_id=db_interview.interview_id,
        question_text=nq["question"],
        topic=nq.get("topic", db_question.topic),
        difficulty=nq.get("difficulty", next_difficulty),
        question_order=next_order,
    )


def build_state(db: Session, db_interview: models.Interview) -> dict:
    """
    Describes exactly where this interview is, so the frontend can continue from there.

    status values:
      not_started          no questions yet
      awaiting_answer      a question is waiting for the candidate's answer
      pending_evaluation   the last answer is saved but not yet evaluated
      needs_next_question  the last answer is evaluated but the next question is missing
      complete             all questions answered and evaluated
    """
    questions = crud.get_questions_for_interview(db, db_interview.interview_id)

    history = []
    current_question = None
    for q in questions:
        a = q.answer
        if a is None:
            current_question = q
            break
        ev = a.evaluation
        history.append(
            {
                "question_id": q.question_id,
                "question": q.question_text,
                "difficulty": q.difficulty,
                "answer": a.answer_text,
                "evaluation": (
                    schemas.EvaluationOut.model_validate(ev).model_dump(mode="json") if ev else None
                ),
            }
        )

    if not questions:
        status = "not_started"
    elif current_question is not None:
        status = "awaiting_answer"
    else:
        last = questions[-1]
        if last.answer.evaluation is None:
            status = "pending_evaluation"
        elif last.question_order >= db_interview.total_questions:
            status = "complete"
        else:
            status = "needs_next_question"

    return {
        "interview_id": db_interview.interview_id,
        "status": status,
        "total_questions": db_interview.total_questions,
        "current_question": (
            schemas.QuestionOut.model_validate(current_question).model_dump(mode="json")
            if current_question
            else None
        ),
        "history": history,
    }