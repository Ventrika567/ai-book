import json
import os
import tempfile
from typing import Any, Dict

from fastapi import APIRouter, File, HTTPException, UploadFile

from llm import call_llm_structured
from models import SyllabusExtraction, SYLLABUS_EXTRACTION_SCHEMA
from pdf_utils import extract_text_from_pdf

router = APIRouter()

EXTRACTION_SYSTEM_PROMPT = """You are an elite academic data extractor specializing in university syllabi. Your goal is to transform messy, unstructured syllabus text into a high-fidelity JSON representation of course materials and academic milestones.

### MISSION:
1. **Identify Textbooks**: Scrape every book mentioned. 
   - Differentiate between 'Required', 'Recommended', and 'Optional' in the `bookname` if possible, but keep the title clean.
   - **Crucial**: Extract `date_periods`. Look for reading schedules, lecture plans, or "Weekly Readings" sections to determine exactly when a book is needed.
   - If the syllabus says "Read Chapters 1-4 in Week 2", create a period for 'Week 2' with the corresponding chapter info in the description.

2. **Map the Academic Timeline**: Capture all quizzes, exams, assignments, projects, and deadlines.
   - Assign the correct `item_type` meticulously.
   - For `start_date` and `end_date`, use current year logic unless specified otherwise.
   - If a date is ambiguous (e.g., "Monday of Week 3"), do your best to estimate the ISO date based on the course's start date if identifiable, otherwise leave the ISO fields empty.

### RULES:
- **Zero Hallucination**: Only extract what is present in the text.
- **Strict JSON**: Return ONLY valid JSON matching the schema. 
- **Completeness**: If a book has an ISBN, extract it; it is the single most important identifier for rental matching.
- **Format**: If a field is unknown, use an empty string. Never use "N/A" or "None" strings."""


@router.post("/extract-syllabus")
async def extract_syllabus(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Upload a PDF syllabus and extract books + schedule items using LLM."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(await file.read())
        temp_path = temp_file.name

    try:
        pdf_text = extract_text_from_pdf(temp_path)
        if not pdf_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from the PDF. It may be scanned or empty.",
            )

        user_prompt = (
            "Extract all textbooks and schedule items from this syllabus:\n\n"
            f"{pdf_text}"
        )

        raw_result = await call_llm_structured(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema=SYLLABUS_EXTRACTION_SCHEMA,
            schema_name="syllabus_extraction",
        )

        # Validate with Pydantic
        validated = SyllabusExtraction.model_validate(raw_result)
        return validated.model_dump()

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass
