from collections import defaultdict
from sqlalchemy.orm import Session
from backend import crud, session_recovery


def generate_candidate_report(db: Session, interview_id: int) -> dict:
    """
    Candidate report covering EVERY question that was asked.
    - Saved answers that were never evaluated are evaluated now (if the AI is available).
    - Anything still missing is listed with a status, not silently dropped.
    """
    db_interview = crud.get_interview(db, interview_id)
    questions = crud.get_questions_for_interview(db, interview_id)

    topic_scores = defaultdict(list)
    all_scores = []
    missing_concepts_all = []
    highest_difficulty_reached = "beginner"
    difficulty_rank = {"beginner": 1, "intermediate": 2, "advanced": 3}

    timeline = []
    pending_evaluation = 0
    unanswered = 0

    for q in questions:
        entry = {
            "question_order": q.question_order,
            "question": q.question_text,
            "difficulty": q.difficulty,
            "answer": None,
            "score": None,
            "knowledge_level": None,
            "feedback": None,
            "status": "not_answered",
        }

        if q.answer is None:
            unanswered += 1
            timeline.append(entry)
            continue

        entry["answer"] = q.answer.answer_text

        # Recover an answer that was saved but never evaluated
        ev = q.answer.evaluation or session_recovery.evaluate_saved_answer(db, q)

        if ev is None:
            pending_evaluation += 1
            entry["status"] = "pending_evaluation"
            timeline.append(entry)
            continue

        score = ev.score or 0
        all_scores.append(score)
        topic_scores[q.topic or "General"].append(score)

        if ev.missing_concepts and ev.missing_concepts.lower() != "none":
            missing_concepts_all.extend([m.strip() for m in ev.missing_concepts.split(",")])

        if difficulty_rank.get(q.difficulty, 0) > difficulty_rank.get(highest_difficulty_reached, 0):
            highest_difficulty_reached = q.difficulty

        entry["score"] = score
        entry["knowledge_level"] = ev.knowledge_level
        entry["feedback"] = ev.feedback
        entry["status"] = "evaluated"
        timeline.append(entry)

    overall_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0

    topic_breakdown = {
        topic: round(sum(scores) / len(scores), 1) for topic, scores in topic_scores.items()
    }

    strengths = [t for t, s in topic_breakdown.items() if s >= 70]
    weaknesses = [t for t, s in topic_breakdown.items() if s < 50]

    total_planned = db_interview.total_questions if db_interview else len(questions)
    report_complete = (
        pending_evaluation == 0 and unanswered == 0 and len(questions) >= total_planned
    )

    return {
        "interview_id": interview_id,
        "report_complete": report_complete,
        "total_questions_planned": total_planned,
        "questions_asked": len(questions),
        "questions_evaluated": len(all_scores),
        "questions_pending_evaluation": pending_evaluation,
        "questions_unanswered": unanswered,
        "overall_score": overall_score,
        "topic_breakdown": topic_breakdown,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "highest_difficulty_reached": highest_difficulty_reached,
        "recommended_focus_areas": list(set(missing_concepts_all))[:5],
        "timeline": timeline,
    }


def generate_interview_quality_report(db: Session, interview_id: int) -> dict:
    questions = crud.get_questions_for_interview(db, interview_id)

    total = len(questions)
    if total == 0:
        return {"interview_id": interview_id, "message": "No questions found for this interview."}

    difficulty_counts = defaultdict(int)
    topics_covered = set()
    question_texts = []

    for q in questions:
        difficulty_counts[q.difficulty or "unknown"] += 1
        topics_covered.add(q.topic or "General")
        question_texts.append(q.question_text.strip().lower())

    difficulty_distribution = {
        level: round((count / total) * 100, 1) for level, count in difficulty_counts.items()
    }

    repeated_questions = total - len(set(question_texts))

    return {
        "interview_id": interview_id,
        "total_questions_asked": total,
        "difficulty_distribution": difficulty_distribution,
        "topics_covered": list(topics_covered),
        "repeated_questions": repeated_questions,
        "adaptive_behavior_detected": len(difficulty_counts) > 1,
    }