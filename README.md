\# Project Altron: Adaptive AI Interview Intelligence Platform



An AI-powered interview platform that builds a role-specific interview from a company's Job Description (JD) and syllabus, adjusts question difficulty based on each answer, and generates performance reports.



\## How it works



```

HR uploads JD / syllabus

&#x20;       |

Text extraction -> chunking -> embeddings -> ChromaDB (one knowledge base per interview)

&#x20;       |

Gemini generates a question grounded in the retrieved context

&#x20;       |

Candidate answers -> answer saved -> Gemini evaluates -> next difficulty chosen

&#x20;       |

Candidate report + interview quality report

```



\## Features



\- \*\*RAG pipeline:\*\* PDF, DOCX and TXT files are chunked, embedded (Sentence Transformers) and stored in ChromaDB.

\- \*\*Adaptive difficulty:\*\* strong answers raise the next question's difficulty, weak answers lower it.

\- \*\*Answer evaluation:\*\* score, knowledge level, confidence, missing concepts and feedback.

\- \*\*Session recovery:\*\* every answer is saved before the AI is called, so an AI outage or lost connection never loses it. An interrupted interview can be resumed by its interview ID.

\- \*\*Reports:\*\* a candidate performance report and an interview quality report (difficulty spread, repeated questions).

\- \*\*Model fallback:\*\* if the main Gemini model is overloaded, requests retry and then switch to a backup model.



\## Tech stack



FastAPI, PostgreSQL, SQLAlchemy, ChromaDB, Sentence Transformers, PyMuPDF, python-docx, LangChain text splitters, Google Gemini API, Streamlit.



\## Setup



The backend and frontend use two separate virtual environments, because their package versions conflict.



\*\*1. Database:\*\* create a PostgreSQL database named `project\_altron`.



\*\*2. Environment file:\*\* create a `.env` file in the project root:



```

DATABASE\_URL=postgresql+psycopg2://postgres:YOUR\_PASSWORD@localhost:5432/project\_altron

GEMINI\_API\_KEY=your\_key\_here

GEMINI\_FALLBACK\_MODEL=gemini-3.1-flash-lite

```



\*\*3. Backend:\*\*



```

python -m venv venv

venv\\Scripts\\activate

python -m pip install -r requirements.txt

python -m uvicorn backend.app:app --reload

```



API docs: http://127.0.0.1:8000/docs



\*\*4. Frontend\*\* (in a second terminal):



```

python -m venv venv\_frontend

venv\_frontend\\Scripts\\activate

python -m pip install -r frontend/requirements.txt

python -m streamlit run frontend\\app.py

```



App: http://localhost:8501



\## Project structure



```

backend/     FastAPI app, models, RAG, question generation, evaluation, reports

frontend/    Streamlit interface

documents/   uploaded files (not tracked)

vector\_store/ ChromaDB data (not tracked)

```



\## Roadmap



\- Interview blueprint (plan topics from the JD)

\- Skill gap analysis

\- Resume and JD matching

\- Follow-up questions

\- Voice interview, proctoring, Google Meet integration

