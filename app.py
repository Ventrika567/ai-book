import json
import os
import tempfile
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, Query, Path
from openai import OpenAI
from pypdf import PdfReader
import httpx
from xml.etree import ElementTree as ET

load_dotenv()

app = FastAPI(title="PDF to JSON with OpenAI")

# ---------- Open Library Search ----------
OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"

@app.get("/search_books", response_model=Dict[str, Any])
async def search_books(
    q: str = Query(..., description="Book title or search query"),
    limit: int = Query(10, ge=1, le=100, description="Number of results to return"),
    fields: Optional[str] = Query(
        None,
        description="Comma-separated fields to return (e.g., 'title,author_name,cover_i')"
    ),
    lang: Optional[str] = Query(None, description="Two-letter language code (e.g., 'en')"),
    sort: Optional[str] = Query(None, description="Sort order (e.g., 'new', 'old')")
):
    """
    Endpoint 1: Search for books by name using the Open Library Search API.
    """
    params: Dict[str, Any] = {"q": q, "limit": limit}
    if fields:
        params["fields"] = fields
    if lang:
        params["lang"] = lang
    if sort:
        params["sort"] = sort

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(OPEN_LIBRARY_SEARCH_URL, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail="Open Library API error")
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")

    return {
        "query": q,
        "total_results": data.get("num_found", 0),
        "results": data.get("docs", [])
    }

# ---------- eCampus Pricing by ISBN ----------
ECAMPUS_URL = "https://api.ecampus.com/service.asmx"
SOAP_ACTION = "http://www.etextbooksnow.com/GetTextbookXInfo"

def build_soap_payload(isbn: str) -> str:
    """Construct the SOAP envelope for GetTextbookXInfo."""
    return f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <GetTextbookXInfo xmlns="http://www.etextbooksnow.com/">
      <ISBN>{isbn}</ISBN>
    </GetTextbookXInfo>
  </soap12:Body>
</soap12:Envelope>"""

def parse_ecampus_response(xml_content: bytes) -> Dict[str, Any]:
    """Parse SOAP response and extract price fields."""
    try:
        root = ET.fromstring(xml_content)
        namespaces = {
            'soap': 'http://www.w3.org/2003/05/soap-envelope',
            'ns': 'http://www.etextbooksnow.com/'
        }
        body = root.find('.//soap:Body', namespaces)
        if body is None:
            body = root.find('.//Body')
        if body is None:
            raise ValueError("Could not locate SOAP Body")

        resp = body.find('.//ns:GetTextbookXInfoResponse', namespaces)
        if resp is None:
            resp = body.find('.//GetTextbookXInfoResponse')
        if resp is None:
            raise ValueError("Could not locate GetTextbookXInfoResponse")

        ebook_price_elem = resp.find('.//ns:EBookPrice', namespaces) or resp.find('.//EBookPrice')
        used_price_elem = resp.find('.//ns:UsedPrice', namespaces) or resp.find('.//UsedPrice')
        ebook_url_elem = resp.find('.//ns:EBookBuyUrl', namespaces) or resp.find('.//EBookBuyUrl')

        if ebook_price_elem is None or used_price_elem is None:
            raise ValueError("Missing price fields in response")

        return {
            "ebook_price": float(ebook_price_elem.text),
            "used_price": float(used_price_elem.text),
            "ebook_url": ebook_url_elem.text if ebook_url_elem is not None else None
        }
    except Exception as e:
        raise ValueError(f"XML parsing failed: {str(e)}")

@app.get("/pricing/{isbn}")
async def get_ecampus_pricing(
    isbn: str = Path(..., description="ISBN-13 or ISBN-10 of the textbook")
):
    """
    Endpoint 2: Retrieve eCampus pricing for a given ISBN.
    """
    payload = build_soap_payload(isbn)

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": SOAP_ACTION,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(
                ECAMPUS_URL,
                content=payload,
                headers=headers,
                follow_redirects=True
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            print(f"Status: {e.response.status_code}")
            print(f"Response text: {e.response.text[:500]}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"eCampus API error: {e.response.text[:200]}"
            )
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")

    try:
        result = parse_ecampus_response(response.content)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse eCampus response: {str(e)}")

    return {"isbn": isbn, **result}

# ---------- Helper: Get ISBN from title via Open Library ----------
async def get_isbn_from_title(title: str) -> Optional[str]:
    """Returns the first ISBN-13 found for the given book title, or None if none found."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            OPEN_LIBRARY_SEARCH_URL,
            params={"q": title, "limit": 1, "fields": "key,title"}
        )
        resp.raise_for_status()
        data = resp.json()
        docs = data.get("docs", [])
        if not docs:
            return None
        work_key = docs[0].get("key")

    if not work_key:
        return None
    editions_url = f"https://openlibrary.org{work_key}/editions.json"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(editions_url, params={"limit": 10})
        resp.raise_for_status()
        editions_data = resp.json()
        for entry in editions_data.get("entries", []):
            if "isbn_13" in entry and entry["isbn_13"]:
                return entry["isbn_13"][0]
            if "isbn_10" in entry and entry["isbn_10"]:
                return entry["isbn_10"][0]
    return None

# ---------- Helper: Call eCampus Pricing ----------
async def get_ecampus_price(isbn: str) -> Dict[str, Any]:
    """Call eCampus SOAP API for a given ISBN."""
    payload = build_soap_payload(isbn)
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": SOAP_ACTION,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(ECAMPUS_URL, content=payload, headers=headers)
        resp.raise_for_status()
        return parse_ecampus_response(resp.content)

# ---------- Endpoint 3: Search by title on eCampus (via Open Library ISBN) ----------
@app.get("/search_ecampus")
async def search_ecampus_by_title(
    title: str = Query(..., description="Book title, e.g., 'The Hobbit'")
):
    """
    Endpoint 3: Search for a book by title, get its ISBN from Open Library,
    then fetch pricing from eCampus.
    """
    isbn = await get_isbn_from_title(title)
    if not isbn:
        raise HTTPException(status_code=404, detail="No ISBN found for this book")

    try:
        price_data = await get_ecampus_price(isbn)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="eCampus API error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pricing error: {str(e)}")

    return {
        "title": title,
        "isbn": isbn,
        "pricing": price_data
    }

# ---------- Endpoint 4: Open Library availability by ISBN ----------
@app.get("/pricing_openlibrary/{isbn}")
async def get_openlibrary_availability(
    isbn: str = Path(..., description="ISBN-13 or ISBN-10")
):
    """
    Endpoint 4: Retrieve Open Library availability information for a given ISBN.
    """
    params = {
        "q": f"isbn:{isbn}",
        "limit": 1,
        "fields": "title,author_name,availability"
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(OPEN_LIBRARY_SEARCH_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail="Open Library API error")
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")

        docs = data.get("docs", [])
        if not docs:
            raise HTTPException(status_code=404, detail="Book not found")

        book = docs[0]
        availability = book.get("availability", {})

    return {
        "isbn": isbn,
        "title": book.get("title"),
        "author": book.get("author_name"),
        "availability": availability
    }

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
