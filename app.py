import json
import os
import tempfile
from typing import Any, Dict, List

from pydantic import BaseModel

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from openai import OpenAI
from pypdf import PdfReader

load_dotenv()

app = FastAPI(title="PDF to JSON with OpenAI")

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY is missing. Put it in your .env file.")

client = OpenAI(api_key=api_key)

BOOK_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "bookname": {"type": "string"},
        "author": {"type": "string"},
        "edition": {"type": "string"},
        "year": {"type": "string"},
    },
    "required": ["bookname", "author", "edition", "year"],
    "additionalProperties": False,
}

DEFAULT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "books": {
            "type": "array",
            "items": BOOK_SCHEMA,
        }
    },
    "required": ["books"],
    "additionalProperties": False,
}


class BookInfo(BaseModel):
    bookname: str
    author: str
    edition: str
    year: str


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a text-based PDF.
    Note: scanned/image PDFs usually need OCR instead.
    """
    reader = PdfReader(file_path)
    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)

    full_text = "\n\n".join(pages).strip()
    return full_text


def call_openai_for_json(pdf_text: str) -> List[Dict[str, Any]]:
    """
    Send extracted PDF text to OpenAI and force structured JSON output.
    """
    if not pdf_text.strip():
        raise ValueError("No text could be extracted from the PDF.")

    response = client.responses.create(
        model="gpt-5-nano",
        input=[
            {
                "role": "system",
                "content": (
                    "You extract book mentions from document text and return only valid JSON. "
                    "Find every distinct book mentioned in the document. "
                    "Return a JSON object with a single key named 'books'. "
                    "The value of 'books' must be an array where each item contains exactly "
                    "these fields: bookname, author, edition, and year. "
                    "If a field is missing in the document, return an empty string for that field. "
                    "Do not include explanations, markdown, or extra keys."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Extract all books mentioned in this document.\n"
                    f"Document text:\n{pdf_text}"
                ),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "pdf_extraction_result",
                "strict": True,
                "schema": DEFAULT_SCHEMA,
            }
        },
    )

    try:
        parsed_json = json.loads(response.output_text)
        books = parsed_json.get("books")
        if not isinstance(parsed_json, dict) or not isinstance(books, list):
            raise ValueError("Model output is not an object with a 'books' array.")
        validated = [BookInfo.model_validate(item).model_dump() for item in books]
    except Exception as exc:
        raise ValueError(f"Failed to parse model output as valid book JSON array: {exc}") from exc

    return validated


@app.get("/")
def root() -> Dict[str, str]:
    return {
        "message": "PDF to JSON API is running. Use POST /parse-pdf"
    }


@app.post("/parse-pdf")
async def parse_pdf(
    file: UploadFile = File(...)
) -> List[Dict[str, Any]]:
    """
    Upload a PDF, extract text, send text to OpenAI, and return a JSON array of books.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(await file.read())
        temp_path = temp_file.name

    try:
        extracted_text = extract_text_from_pdf(temp_path)

        if not extracted_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from the PDF. It may be scanned or empty."
            )

        result = call_openai_for_json(
            pdf_text=extracted_text,
        )

        if not isinstance(result, list):
            raise HTTPException(status_code=500, detail="AI did not return a JSON array matching the schema")

        return result

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass
