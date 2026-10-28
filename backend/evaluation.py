import json
from backend.question_gen import get_client
from backend import rag


def evaluate_answer(interview_id: int, question_text: str, answer_text: str, current_difficulty: str) -> dict:
    context_chunks = rag.query_knowledge_base(interview_id, question_text, n_results=3)
    context_text = "\n---\n".join(context_chunks) if context_chunks else "No specific context found."

    prompt = f"""You are an expert technical interviewer evaluating a candidate's answer.

Question asked (difficulty: {current_difficulty}):
{question_text}

Candidate's answer:
{answer_text}

Reference context (from the job description/syllabus, for checking correctness):
{context_text}

Evaluate the answer and return ONLY valid JSON, no markdown, no explanation, in this exact format:

{{
  "score": <number 0-100>,
  "knowledge_level": "<beginner|intermediate|advanced>",
  "confidence": "<low|medium|high>",
  "missing_concepts": "<comma-separated key concepts the answer missed, or 'none'>",
  "feedback": "<one or two sentence explanation of the judgment>",
  "next_difficulty": "<beginner|intermediate|advanced>"
}}

Rules for next_difficulty:
- If score >= 80: increase difficulty one level (or keep 'advanced' if already there)
- If score is 50-79: keep the same difficulty
- If score < 50: decrease difficulty one level (or keep 'beginner' if already there)
"""

    client = get_client()
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )

    raw_text = response.text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        result = {
            "score": 50,
            "knowledge_level": "intermediate",
            "confidence": "medium",
            "missing_concepts": "unable to parse AI response",
            "feedback": raw_text,
            "next_difficulty": current_difficulty,
        }

    return result