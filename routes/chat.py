import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from llm import call_llm_text
from models import StudyPlannerRequest, StudyPlannerUserContext, ChatMessage

router = APIRouter()

# ---------------------------------------------------------------------------
# Session store
# ---------------------------------------------------------------------------

_sessions: Dict[str, Dict[str, Any]] = {}
_SESSION_TTL = timedelta(hours=2)


def _sweep_sessions() -> None:
    cutoff = datetime.utcnow() - _SESSION_TTL
    expired = [sid for sid, s in _sessions.items() if s["created_at"] < cutoff]
    for sid in expired:
        del _sessions[sid]


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class StartChatRequest(BaseModel):
    analysis: Dict[str, Any]  # {books, schedule_items}


class ChatMessageRequest(BaseModel):
    session_id: str
    user_message: str


# ---------------------------------------------------------------------------
# Shared prompt builder
# ---------------------------------------------------------------------------

STUDY_PLANNER_SYSTEM_PROMPT = """You are the **SmartRent AI Assistant**. Your goal is to provide **fast, concise** answers about a student's course schedule and textbooks based on the analyzed syllabus.

### GUIDELINES:
1. **Focus**: Only answer questions about the course schedule (exams, deadlines) or the textbooks (required readings, rental periods). 
2. **Conciseness**: Keep responses brief. Use bullet points or short sentences. Avoid lengthy explanations.
3. **Strategic**: If asked about a book, highlight the active reading dates and the best rental option identified.
4. **Style**: Use clean Markdown. No fluff. Get straight to the data.
5. THE YEAR IS 2026
### PROHIBITED:
- No general study tips unless specifically asked about the syllabus timeline.
- No hallucinating dates or prices.
- No verbosity."""


def _build_user_prompt(
    analysis: Dict[str, Any],
    user_context: StudyPlannerUserContext,
    user_message: str,
    chat_history: List[ChatMessage],
) -> str:
    history_lines = [f"{m.role}: {m.content}" for m in chat_history[-8:]]

    return (
        "Student context:\n"
        f"- Known topics: {user_context.known_topics or 'Not provided'}\n"
        f"- Budget: {user_context.budget or 'Not provided'}\n"
        f"- Preferred textbook format: {user_context.textbook_format_preference or 'Not provided'}\n"
        f"- Exam dates flexibility: {user_context.exam_date_flexibility or 'Not provided'}\n\n"
        f"Syllabus analysis JSON:\n{json.dumps(analysis, indent=2)}\n\n"
        f"Recent chat history:\n{chr(10).join(history_lines) if history_lines else 'None'}\n\n"
        f"Latest student message:\n{user_message}"
    )


# ---------------------------------------------------------------------------
# Session-based endpoints (new)
# ---------------------------------------------------------------------------

@router.post("/chat/start")
async def start_chat_session(payload: StartChatRequest) -> Dict[str, str]:
    """Create a new chat session storing the syllabus analysis server-side."""
    if not payload.analysis.get("books"):
        raise HTTPException(status_code=400, detail="Analysis must include at least one book.")
    _sweep_sessions()
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "analysis": payload.analysis,
        "history": [],
        "created_at": datetime.utcnow(),
    }
    return {"session_id": session_id}


@router.post("/chat/message")
async def send_chat_message(payload: ChatMessageRequest) -> Dict[str, Any]:
    """Send a message to an existing session; history is stored server-side."""
    session = _sessions.get(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    history: List[ChatMessage] = session["history"]
    user_prompt = _build_user_prompt(
        analysis=session["analysis"],
        user_context=StudyPlannerUserContext(),
        user_message=payload.user_message,
        chat_history=history,
    )

    try:
        answer = await call_llm_text(
            system_prompt=STUDY_PLANNER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        if not answer:
            raise ValueError("LLM returned an empty response.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    history.append(ChatMessage(role="user", content=payload.user_message))
    history.append(ChatMessage(role="assistant", content=answer))
    return {"assistant_message": answer}


# ---------------------------------------------------------------------------
# Legacy stateless endpoint (kept for backwards compatibility)
# ---------------------------------------------------------------------------

@router.post("/chat-study-plan")
async def chat_study_plan(payload: StudyPlannerRequest) -> Dict[str, Any]:
    """Generate a personalized study and textbook access strategy (stateless)."""
    if not payload.analysis.get("books"):
        raise HTTPException(status_code=400, detail="Analysis payload must include at least one detected book.")

    try:
        user_prompt = _build_user_prompt(
            analysis=payload.analysis,
            user_context=payload.user_context,
            user_message=payload.user_message,
            chat_history=payload.chat_history,
        )

        answer = await call_llm_text(
            system_prompt=STUDY_PLANNER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        if not answer:
            raise ValueError("Study planner did not return a response.")

        return {"assistant_message": answer}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
