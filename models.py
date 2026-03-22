from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ---------- Syllabus Extraction Models ----------

class DatePeriod(BaseModel):
    description: str = ""
    start_date: str = ""
    end_date: str = ""


class ExtractedBook(BaseModel):
    bookname: str
    author: str = ""
    edition: str = ""
    year: str = ""
    isbn: str = ""
    date_periods: List[DatePeriod] = []


class ExtractedScheduleItem(BaseModel):
    item_type: str  # exam, quiz, homework, assignment, reading, project, deadline, other
    label: str
    date_text: str
    start_date: str = ""
    end_date: str = ""


class SyllabusExtraction(BaseModel):
    books: List[ExtractedBook]
    schedule_items: List[ExtractedScheduleItem]


# ---------- Provider Models ----------

class ProviderDetail(BaseModel):
    provider: str
    book_info: Dict[str, Any] = {}
    estimated_cost: Optional[float] = None
    acquisition_mode: str = ""  # "buy", "borrow", "free"
    price_type: str = ""  # "ebook", "used", "new", "google_books", etc.
    provider_link: str = ""
    provider_book_id: str = ""


class BookProviderResults(BaseModel):
    """All provider results for a single book."""
    bookname: str
    providers: List[ProviderDetail] = []


class BestProviderSelection(BaseModel):
    bookname: str
    best_provider: Optional[ProviderDetail] = None
    reason: str = ""


# ---------- Final Result ----------

class FinalResult(BaseModel):
    bookname: str
    author: str = ""
    edition: str = ""
    year: str = ""
    isbn: str = ""
    best_provider: Optional[ProviderDetail] = None
    date_periods: List[DatePeriod] = []
    schedule_items: List[ExtractedScheduleItem] = []


# ---------- Chat / Study Planner ----------

class StudyPlannerUserContext(BaseModel):
    known_topics: str = ""
    budget: str = ""
    textbook_format_preference: str = ""
    exam_date_flexibility: str = ""


class ChatMessage(BaseModel):
    role: str
    content: str


class StudyPlannerRequest(BaseModel):
    analysis: Dict[str, Any]
    user_context: StudyPlannerUserContext
    user_message: str
    chat_history: List[ChatMessage] = []


# ---------- JSON Schemas for Structured Output ----------

DATE_PERIOD_SCHEMA = {
    "type": "object",
    "properties": {
        "description": {"type": "string"},
        "start_date": {"type": "string"},
        "end_date": {"type": "string"},
    },
    "required": ["description", "start_date", "end_date"],
    "additionalProperties": False,
}

EXTRACTED_BOOK_SCHEMA = {
    "type": "object",
    "properties": {
        "bookname": {"type": "string"},
        "author": {"type": "string"},
        "edition": {"type": "string"},
        "year": {"type": "string"},
        "isbn": {"type": "string"},
        "date_periods": {
            "type": "array",
            "items": DATE_PERIOD_SCHEMA,
        },
    },
    "required": ["bookname", "author", "edition", "year", "isbn", "date_periods"],
    "additionalProperties": False,
}

SCHEDULE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "item_type": {
            "type": "string",
            "enum": ["exam", "quiz", "homework", "assignment", "reading", "lecture", "deadline", "project", "other"],
        },
        "label": {"type": "string"},
        "date_text": {"type": "string"},
        "start_date": {"type": "string"},
        "end_date": {"type": "string"},
    },
    "required": ["item_type", "label", "date_text", "start_date", "end_date"],
    "additionalProperties": False,
}

SYLLABUS_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "books": {
            "type": "array",
            "items": EXTRACTED_BOOK_SCHEMA,
        },
        "schedule_items": {
            "type": "array",
            "items": SCHEDULE_ITEM_SCHEMA,
        },
    },
    "required": ["books", "schedule_items"],
    "additionalProperties": False,
}

BOOK_MATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "best_match_index": {"type": "integer"},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["best_match_index", "confidence", "reason"],
    "additionalProperties": False,
}

BEST_PROVIDER_SCHEMA = {
    "type": "object",
    "properties": {
        "best_provider_index": {"type": "integer"},
        "reason": {"type": "string"},
    },
    "required": ["best_provider_index", "reason"],
    "additionalProperties": False,
}
