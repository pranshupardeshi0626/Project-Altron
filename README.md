<div align="center">



\# Project Altron



\### Adaptive AI Interview Intelligence Platform



\*\*Upload a job description. Get a role-specific AI interviewer that adapts to every answer.\*\*



!\[Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python\&logoColor=white)

!\[FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi\&logoColor=white)

!\[PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql\&logoColor=white)

!\[ChromaDB](https://img.shields.io/badge/ChromaDB-RAG-FF6F00)

!\[Gemini](https://img.shields.io/badge/Google%20Gemini-4285F4?logo=google\&logoColor=white)

!\[Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit\&logoColor=white)



</div>



\---



\## Why this exists



Technical interviews are slow to prepare, inconsistent between interviewers, and hard to scale. Most "AI interview" tools are just chatbots that ask generic questions.



Project Altron works differently. It reads \*\*your\*\* job description and syllabus, builds a private knowledge base for that role, and runs an interview that \*\*changes difficulty in real time\*\* based on how well the candidate answers. Afterwards it produces a candidate report and a report on the quality of the interview itself.



<!--

Add a demo GIF here once you have one. A short screen recording of a full interview is the single best way to attract stars:

!\[Demo](docs/demo.gif)

\-->



\## Features



| | |

|---|---|

| \*\*Role-specific questions\*\* | Questions are generated from your JD and syllabus using RAG, not from generic prompts. |

| \*\*Adaptive difficulty\*\* | Strong answers raise the next question's difficulty, weak answers lower it. |

| \*\*Structured evaluation\*\* | Every answer gets a score, knowledge level, confidence, missing concepts and written feedback. |

| \*\*Never loses an answer\*\* | Answers are saved \*before\* the AI is called. If the AI service fails or the connection drops, the interview resumes exactly where it stopped. |

| \*\*Two reports\*\* | A candidate performance report, and an interview quality report that flags repeated questions and checks the difficulty spread. |

| \*\*No repeated questions\*\* | Previously asked questions are passed to the model so it does not repeat them. |

| \*\*Resilient AI calls\*\* | Automatic retries with backoff, then a fallback to a second Gemini model when the first is overloaded. |

| \*\*Multi-format documents\*\* | PDF, DOCX and TXT uploads, processed automatically. |



\## How it works



```mermaid

flowchart TD

&#x20;   A\[HR uploads JD and syllabus] --> B\[Extract text and chunk]

&#x20;   B --> C\[Embed with Sentence Transformers]

&#x20;   C --> D\[(ChromaDB: one knowledge base per interview)]

&#x20;   D --> E\[Retrieve relevant context]

&#x20;   E --> F\[Gemini generates a question]

&#x20;   F --> G\[Candidate answers]

&#x20;   G --> H\[(Answer saved to PostgreSQL)]

&#x20;   H --> I\[Gemini evaluates the answer]

&#x20;   I --> J{Score}

&#x20;   J -->|80 or above| K\[Harder next question]

&#x20;   J -->|50 to 79| L\[Same difficulty]

&#x20;   J -->|below 50| M\[Easier next question]

&#x20;   K --> F

&#x20;   L --> F

&#x20;   M --> F

&#x20;   I --> N\[Candidate and quality reports]

```



The system does \*\*not\*\* retrain a model for each job description. The LLM already has the general knowledge, and the uploaded documents act as a temporary, role-specific knowledge base (Retrieval Augmented Generation).



\### Session recovery



Each submission follows a fixed order so nothing can be lost:



1\. Save the answer to PostgreSQL.

2\. Evaluate it with Gemini. If this fails, the answer stays saved with no evaluation, which means "pending".

3\. Generate the next question. If this fails, the evaluation is already saved.

4\. `POST /interviews/{id}/resume` finds the first unfinished step and completes it.



Reports include every question that was asked. An answer that was saved but never evaluated is evaluated when the report is built, and anything still unavailable is listed with a status instead of being dropped.



\## Tech stack



| Layer | Technology |

|---|---|

| Backend | FastAPI, SQLAlchemy |

| Database | PostgreSQL |

| Vector store | ChromaDB |

| Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`) |

| Document parsing | PyMuPDF, python-docx |

| Chunking | LangChain text splitters |

| LLM | Google Gemini API (with fallback model) |

| Frontend | Streamlit |



\## Quick start



\*\*Requirements:\*\* Python 3.11 or newer, PostgreSQL, and a free \[Gemini API key](https://aistudio.google.com/apikey).



The backend and frontend use \*\*separate virtual environments\*\* because their package versions conflict.



\### 1. Clone and create the database



```bash

git clone https://github.com/YOUR\_USERNAME/Project-Altron.git

cd Project-Altron

```



Create an empty PostgreSQL database named `project\_altron`. Tables are created automatically on first start.



\### 2. Configure



Create a `.env` file in the project root:



```env

DATABASE\_URL=postgresql+psycopg2://postgres:YOUR\_PASSWORD@localhost:5432/project\_altron

GEMINI\_API\_KEY=your\_gemini\_api\_key

GEMINI\_FALLBACK\_MODEL=gemini-3.1-flash-lite

```



| Variable | Required | Purpose |

|---|---|---|

| `DATABASE\_URL` | Yes | PostgreSQL connection string |

| `GEMINI\_API\_KEY` | Yes | Gemini API key |

| `GEMINI\_MODEL` | No | Primary model (default `gemini-3.6-flash`) |

| `GEMINI\_FALLBACK\_MODEL` | No | Backup model used when the primary is overloaded |



\### 3. Run the backend



```bash

python -m venv venv

venv\\Scripts\\activate          # macOS/Linux: source venv/bin/activate

python -m pip install -r requirements.txt

python -m uvicorn backend.app:app --reload

```



The first run downloads the embedding model, which can take a minute.

Interactive API docs: http://127.0.0.1:8000/docs



\### 4. Run the frontend



In a second terminal:



```bash

python -m venv venv\_frontend

venv\_frontend\\Scripts\\activate  # macOS/Linux: source venv\_frontend/bin/activate

python -m pip install -r frontend/requirements.txt

python -m streamlit run frontend/app.py

```



App: http://localhost:8501



\### 5. Try it



1\. Create an interview in the sidebar.

2\. Upload a JD, syllabus or any study material (PDF, DOCX or TXT).

3\. Enter a starting topic and start the interview.

4\. Answer the questions and watch the difficulty adapt.

5\. Open the candidate and quality reports.



\## API overview



| Method | Endpoint | Description |

|---|---|---|

| `POST` |

