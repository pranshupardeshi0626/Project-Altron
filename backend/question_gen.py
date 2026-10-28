import os
import json
import time
import random
from google import genai
from google.genai import errors
from dotenv import load_dotenv
from backend import rag

load_dotenv()

_client = None

PRIMARY_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "")
RETRYABLE_CODES = (429, 500, 503, 504)
RETRIES_PER_MODEL = 4


def get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        _client = genai.Client(api_key=api_key)
    return _client


def call_gemini(prompt: str) -> str:
    """
    Calls Gemini. If the primary model is overloaded it retries with a growing wait,
    then switches to the backup model. A model that does not exist is skipped at once.
    """
    client = get_client()
    models_to_try = [PRIMARY_MODEL]
    if FALLBACK_MODEL and FALLBACK_MODEL != PRIMARY_MODEL:
        models_to_try.append(FALLBACK_MODEL)

    last_error = None
    for model_name in models_to_try:
        for attempt in range(RETRIES_PER_MODEL):
            try:
                response = client.models.generate_content(model=model_name, contents=prompt)
                return response.text.strip()
            except errors.APIError as e:
                last_error = e
                code = getattr(e, "code", None)
                if code == 404:
                    break  # this model name does not exist, try the next one
                if code not in RETRYABLE_CODES:
                    raise
                time.sleep(2 ** attempt + random.random())

    raise last_error


def generate_questions(
    interview_id: int,
    topic: str,
    difficulty: str,
    num_questions: int = 3,
    avoid_questions: list[str] | None = None,
) -> list[dict]:
    context_chunks = rag.query_knowledge_base(interview_id, topic, n_results=5)
    context_text = "\n---\n".join(context_chunks) if context_chunks else "No specific context found."

    avoid_text = ""
    if avoid_questions:
        avoid_text = (
            "\n\nDo NOT repeat or closely paraphrase any of these previously asked questions:\n"
            + "\n".join(f"- {q}" for q in avoid_questions)
        )

    prompt = f"""You are an expert technical interviewer.

Based on the following job description / syllabus context, generate {num_questions} interview questions
on the topic "{topic}" at "{difficulty}" difficulty level.

Context from the job description/syllabus:
{context_text}{avoid_text}

Rules:
- Questions must be relevant to the context above and the topic.
- Difficulty must genuinely match "{difficulty}" (beginner = definitions/basics, intermediate = applied scenarios, advanced = deep/edge-case/optimization).
- Return ONLY valid JSON, no markdown, no explanation, in this exact format:

[
  {{"question": "...", "topic": "{topic}", "difficulty": "{difficulty}"}},
  {{"question": "...", "topic": "{topic}", "difficulty": "{difficulty}"}}
]
"""

    raw_text = call_gemini(prompt)

    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        questions = json.loads(raw_text)
    except json.JSONDecodeError:
        return [{"question": raw_text, "topic": topic, "difficulty": difficulty, "parse_error": True}]

    return questions