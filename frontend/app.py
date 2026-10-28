import requests
import streamlit as st

API_BASE = "http://127.0.0.1:8000"
TIMEOUT = 180  # Gemini retries can take a while

st.set_page_config(page_title="Project Altron - AI Interview", layout="centered")
st.title("Adaptive AI Interview Platform")

# ---------- Session state ----------
defaults = {
    "interview_id": None,
    "current_question": None,
    "history": [],
    "interview_complete": False,
    "needs_resume": False,   # an answer is saved but an AI step is still unfinished
    "unsent_answer": None,   # an answer that did not reach the backend
    "notice": None,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def call_backend(method, path, **kwargs):
    """Returns the response, or None if the backend cannot be reached."""
    try:
        return requests.request(method, f"{API_BASE}{path}", timeout=TIMEOUT, **kwargs)
    except requests.exceptions.RequestException:
        return None


def api_error(resp):
    if resp is None:
        st.error("Cannot reach the backend. Check that the uvicorn window is running.")
        return
    try:
        detail = resp.json().get("detail", resp.text)
    except Exception:
        detail = resp.text
    st.error(f"Failed ({resp.status_code}): {detail}")


def apply_state(state):
    """Loads the interview state from the database into the page."""
    st.session_state.interview_id = state["interview_id"]
    st.session_state.history = state["history"]
    st.session_state.current_question = state["current_question"]
    status = state["status"]
    st.session_state.interview_complete = status == "complete"
    st.session_state.needs_resume = status in ("pending_evaluation", "needs_next_question")
    st.session_state.unsent_answer = None


def resume_interview(interview_id):
    """Asks the backend to finish any interrupted step, then loads the state."""
    with st.spinner("Resuming the interview..."):
        resp = call_backend("POST", f"/interviews/{interview_id}/resume")
    if resp is not None and resp.status_code == 200:
        apply_state(resp.json())
        st.session_state.notice = None
        return True
    api_error(resp)
    return False


def send_answer(question_id, answer_text):
    """Sends an answer. The backend saves it first, so it is kept even if the AI fails."""
    interview_id = st.session_state.interview_id
    with st.spinner("Saving and evaluating your answer..."):
        resp = call_backend(
            "POST",
            f"/interviews/{interview_id}/submit-answer",
            json={"question_id": question_id, "answer_text": answer_text},
        )

    if resp is None or resp.status_code != 200:
        # The answer may not have reached the database. Keep it here so it can be re-sent.
        st.session_state.unsent_answer = {"question_id": question_id, "answer_text": answer_text}
        if resp is None:
            st.session_state.notice = "Could not reach the server. Your answer is kept on this page."
        else:
            st.session_state.notice = f"The server returned an error ({resp.status_code}). Your answer is kept on this page."
        return

    result = resp.json()
    state_resp = call_backend("GET", f"/interviews/{interview_id}/state")
    if state_resp is not None and state_resp.status_code == 200:
        apply_state(state_resp.json())
    else:
        st.session_state.needs_resume = True
        st.session_state.unsent_answer = None

    if result.get("status") == "ok":
        st.session_state.notice = None
    else:
        st.session_state.notice = result.get("message")


# ---------- Sidebar ----------
with st.sidebar:
    st.header("HR Setup")

    title = st.text_input("Interview Title", "Data Analyst Interview")
    role = st.text_input("Role", "Data Analyst")
    experience_level = st.selectbox("Experience Level", ["Fresher", "Junior", "Mid", "Senior"])
    duration_minutes = st.number_input("Duration (minutes)", min_value=5, value=30)
    total_questions = st.number_input("Number of Questions", min_value=1, max_value=10, value=3)

    if st.button("1. Create Interview"):
        resp = call_backend(
            "POST",
            "/interviews/",
            json={
                "title": title,
                "role": role,
                "experience_level": experience_level,
                "duration_minutes": int(duration_minutes),
                "total_questions": int(total_questions),
            },
        )
        if resp is not None and resp.status_code == 200:
            st.session_state.interview_id = resp.json()["interview_id"]
            st.session_state.current_question = None
            st.session_state.history = []
            st.session_state.interview_complete = False
            st.session_state.needs_resume = False
            st.session_state.unsent_answer = None
            st.session_state.notice = None
            st.success(f"Interview created. ID: {st.session_state.interview_id}")
        else:
            api_error(resp)

    st.divider()

    jd_file = st.file_uploader("Upload JD / Syllabus", type=["pdf", "docx", "txt"])
    if st.button("2. Upload Document"):
        if not st.session_state.interview_id:
            st.warning("Create an interview first.")
        elif not jd_file:
            st.warning("Choose a file first.")
        else:
            resp = call_backend(
                "POST",
                f"/interviews/{st.session_state.interview_id}/upload",
                files={"jd_file": (jd_file.name, jd_file.getvalue())},
            )
            if resp is not None and resp.status_code == 200:
                st.success(f"Uploaded. Chunks stored: {resp.json()['jd_chunks_stored']}")
            else:
                api_error(resp)

    st.divider()

    topic = st.text_input("Topic to start with", "PCA")
    if st.button("3. Start Interview"):
        if not st.session_state.interview_id:
            st.warning("Create an interview first.")
        else:
            with st.spinner("Generating first question..."):
                resp = call_backend(
                    "POST",
                    f"/interviews/{st.session_state.interview_id}/start",
                    params={"topic": topic},
                )
            if resp is not None and resp.status_code == 200:
                st.session_state.current_question = resp.json()
                st.session_state.history = []
                st.session_state.interview_complete = False
                st.session_state.needs_resume = False
                st.session_state.unsent_answer = None
                st.session_state.notice = None
                st.success("Interview started.")
            else:
                api_error(resp)

    st.divider()
    st.header("Resume an interview")
    st.caption("Use this if the page was closed or the session broke.")
    resume_id = st.number_input("Interview ID", min_value=1, step=1, value=1)
    if st.button("Resume this interview"):
        if resume_interview(int(resume_id)):
            st.rerun()

# ---------- Main area ----------
if st.session_state.interview_id is None:
    st.info("Use the sidebar to create an interview, or resume an existing one by its ID.")
    st.stop()

st.subheader(f"Interview ID: {st.session_state.interview_id}")
st.caption("Write this ID down. You can use it to resume the interview if the session breaks.")

# Past questions, answers and evaluations
for item in st.session_state.history:
    with st.chat_message("assistant"):
        st.write(f"**[{item['difficulty']}]** {item['question']}")
    with st.chat_message("user"):
        st.write(item["answer"])
    ev = item.get("evaluation")
    if ev:
        with st.expander("See evaluation"):
            st.write(f"**Score:** {ev.get('score')}/100")
            st.write(f"**Knowledge level:** {ev.get('knowledge_level')}")
            st.write(f"**Confidence:** {ev.get('confidence')}")
            st.write(f"**Feedback:** {ev.get('feedback')}")
            st.write(f"**Missing concepts:** {ev.get('missing_concepts')}")
    else:
        st.info("Your answer is saved. Its evaluation is still pending.")

if st.session_state.notice:
    st.warning(st.session_state.notice)

# An answer that never reached the backend
if st.session_state.unsent_answer:
    st.warning("Your last answer has not been confirmed by the server.")
    st.write(st.session_state.unsent_answer["answer_text"])
    if st.button("Retry sending my answer"):
        pending = st.session_state.unsent_answer
        st.session_state.unsent_answer = None
        send_answer(pending["question_id"], pending["answer_text"])
        st.rerun()

# An answer is saved but an AI step is unfinished
elif st.session_state.needs_resume:
    st.warning("The AI service was unavailable for one step. Nothing is lost. Click Resume to finish it.")
    if st.button("Resume interview"):
        if resume_interview(st.session_state.interview_id):
            st.rerun()

elif st.session_state.interview_complete:
    st.success("Interview complete. Thank you.")

elif st.session_state.current_question:
    q = st.session_state.current_question
    with st.chat_message("assistant"):
        st.write(f"**[{q['difficulty']}]** {q['question_text']}")

    answer = st.chat_input("Type your answer here...")
    if answer:
        send_answer(q["question_id"], answer)
        st.rerun()

else:
    st.info("Set a topic in the sidebar and click 3. Start Interview.")

# ---------- Reports ----------
if st.session_state.history:
    st.divider()
    st.subheader("Reports")
    col1, col2 = st.columns(2)
    with col1:
        show_candidate = st.button("Candidate Report")
    with col2:
        show_quality = st.button("Interview Quality Report")

    if show_candidate:
        with st.spinner("Building the report..."):
            resp = call_backend("GET", f"/interviews/{st.session_state.interview_id}/report/candidate")
        if resp is not None and resp.status_code == 200:
            r = resp.json()
            if not r["report_complete"]:
                st.warning(
                    f"This report is not complete yet: {r['questions_asked']} of "
                    f"{r['total_questions_planned']} questions asked, "
                    f"{r['questions_pending_evaluation']} waiting for evaluation."
                )
            st.metric("Overall score", f"{r['overall_score']}/100")
            st.write(f"**Questions evaluated:** {r['questions_evaluated']} of {r['total_questions_planned']}")
            st.write(f"**Highest difficulty reached:** {r['highest_difficulty_reached']}")
            st.write(f"**Strengths:** {', '.join(r['strengths']) or 'None yet'}")
            st.write(f"**Weaknesses:** {', '.join(r['weaknesses']) or 'None'}")
            if r["recommended_focus_areas"]:
                st.write("**Recommended focus areas:**")
                for area in r["recommended_focus_areas"]:
                    st.write(f"- {area}")
            st.write("**Question by question:**")
            for t in r["timeline"]:
                score = t["score"] if t["score"] is not None else "-"
                st.write(f"{t['question_order']}. [{t['difficulty']}] score: {score} ({t['status']})")
        else:
            api_error(resp)

    if show_quality:
        resp = call_backend("GET", f"/interviews/{st.session_state.interview_id}/report/quality")
        if resp is not None and resp.status_code == 200:
            r = resp.json()
            st.write(f"**Total questions asked:** {r['total_questions_asked']}")
            st.write(f"**Repeated questions:** {r['repeated_questions']}")
            st.write(f"**Adaptive behavior detected:** {r['adaptive_behavior_detected']}")
            st.write(f"**Topics covered:** {', '.join(r['topics_covered'])}")
            st.write("**Difficulty distribution (%):**")
            st.json(r["difficulty_distribution"])
        else:
            api_error(resp)