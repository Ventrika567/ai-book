import asyncio
import datetime as dt
import json
import os
import re
import tempfile
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from pydantic import BaseModel

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pypdf import PdfReader
import httpx
from xml.etree import ElementTree as ET

load_dotenv()

app = FastAPI(title="PDF to JSON with OpenAI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Open Library Search ----------
OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json" #RENT
OPEN_LIBRARY_WORK_URL = "https://openlibrary.org" 
OPEN_LIBRARY_BOOK_URL = "https://openlibrary.org/isbn"
GOOGLE_BOOKS_VOLUMES_URL = "https://www.googleapis.com/books/v1/volumes"
INTERNET_ARCHIVE_ADVANCED_SEARCH_URL = "https://archive.org/advancedsearch.php"
HATHITRUST_ISBN_API_URL = "https://catalog.hathitrust.org/api/volumes/brief/isbn"
WORLDCAT_SEARCH_V2_URL = "https://americas.discovery.api.oclc.org/worldcat/search/v2/bibs"
DOAB_SEARCH_URL = "https://directory.doabooks.org/rest/search"
OAPEN_SEARCH_URL = "https://library.oapen.org/rest/search"
BASE_URL = "https://api.openalex.org/works"

GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY", "")
WORLDCAT_API_KEY = os.getenv("WORLDCAT_API_KEY", "")
PRIMO_API_KEY = os.getenv("PRIMO_API_KEY", "")
PRIMO_BASE_URL = os.getenv("PRIMO_BASE_URL", "")
PRIMO_VIEW = os.getenv("PRIMO_VIEW", "")
EDS_PROFILE = os.getenv("EDS_PROFILE", "")
EDS_API_TOKEN = os.getenv("EDS_API_TOKEN", "")
EDS_BASE_URL = os.getenv("EDS_BASE_URL", "https://eds-api.ebscohost.com/edsapi/publication/search")
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY")


def normalize_book_lookup_title(title: str) -> str:
    normalized = (title or "").strip()
    if not normalized:
        return ""

    normalized = re.sub(r"\b\d+(st|nd|rd|th)\s+ed(\.|ition)?\b", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bed(\.|ition)?\b", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\([^)]*\)", "", normalized)
    normalized = re.sub(r"[,:\-]\s*$", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip(" ,:-")
    return normalized


def extract_first_isbn(value: str) -> Optional[str]:
    if not value:
        return None
    match = re.search(r"(97[89]\d{10}|\d{9}[\dXx])", value.replace("-", "").replace(" ", ""))
    return match.group(1) if match else None


def extract_edition_number(value: str) -> Optional[int]:
    if not value:
        return None
    match = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\b", value.lower())
    return int(match.group(1)) if match else None


def build_edition_text(entry: Dict[str, Any]) -> str:
    text_parts: List[str] = []
    for key in ["title", "subtitle", "by_statement", "edition_name"]:
        field = entry.get(key)
        if isinstance(field, list):
            text_parts.extend(str(item) for item in field)
        elif field:
            text_parts.append(str(field))

    for publisher in entry.get("publishers", []) or []:
        if isinstance(publisher, str):
            text_parts.append(publisher)

    return " ".join(text_parts)


def score_openlibrary_edition_candidate(
    entry: Dict[str, Any],
    requested_title: str,
    requested_author: str,
    requested_edition: str,
    requested_isbn: Optional[str],
) -> int:
    score = 0
    entry_isbns = [isbn for key in ["isbn_13", "isbn_10"] for isbn in entry.get(key, [])]
    if requested_isbn and requested_isbn in entry_isbns:
        score += 1000

    requested_edition_number = extract_edition_number(requested_edition)
    entry_text = normalize_text(build_edition_text(entry))
    entry_edition_number = extract_edition_number(entry_text)
    if requested_edition_number is not None:
        if entry_edition_number == requested_edition_number:
            score += 200
        elif entry_edition_number is not None:
            score -= 150

    for token in keyword_tokens(requested_title):
        if token in entry_text:
            score += 10
    for token in keyword_tokens(requested_author):
        if token in entry_text:
            score += 6

    return score


def build_edition_warning(requested_edition: str, entry: Dict[str, Any]) -> Optional[str]:
    requested_edition_number = extract_edition_number(requested_edition)
    matched_edition_number = extract_edition_number(build_edition_text(entry))
    if requested_edition_number is not None and matched_edition_number is not None and requested_edition_number != matched_edition_number:
        return f"Requested {requested_edition_number} edition, but the best provider match appears to be edition {matched_edition_number}."
    if requested_edition_number is not None and matched_edition_number is None:
        return "Requested edition could not be verified from provider data."
    return None


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def keyword_tokens(value: str) -> List[str]:
    return [token for token in normalize_text(value).split() if len(token) > 2]


def build_book_lookup_request(book_or_title: Any) -> Dict[str, str]:
    if isinstance(book_or_title, dict):
        return {
            "title": (book_or_title.get("bookname") or "").strip(),
            "author": (book_or_title.get("author") or "").strip(),
            "edition": (book_or_title.get("edition") or "").strip(),
            "isbn": extract_first_isbn(book_or_title.get("isbn", "")) or "",
        }
    return {"title": str(book_or_title or "").strip(), "author": "", "edition": "", "isbn": ""}


def score_provider_candidate(
    *,
    requested_book: Dict[str, str],
    candidate_title: str,
    candidate_authors: List[str],
    candidate_edition_text: str = "",
    candidate_isbns: Optional[List[str]] = None,
) -> Dict[str, Any]:
    requested_title = requested_book.get("title", "")
    requested_author = requested_book.get("author", "")
    requested_edition = requested_book.get("edition", "")
    requested_isbn = requested_book.get("isbn") or None

    candidate_title_norm = normalize_text(candidate_title)
    candidate_author_norm = normalize_text(" ".join(candidate_authors))
    candidate_edition_norm = normalize_text(candidate_edition_text)
    title_tokens = keyword_tokens(requested_title)
    author_tokens = keyword_tokens(requested_author)
    candidate_isbns = candidate_isbns or []

    score = 0
    title_overlap = sum(1 for token in title_tokens if token in candidate_title_norm)
    author_overlap = sum(1 for token in author_tokens if token in candidate_author_norm)

    if requested_isbn and requested_isbn in candidate_isbns:
        score += 1000

    if title_tokens:
        score += title_overlap * 18
        if title_overlap == len(title_tokens):
            score += 80
        elif len(title_tokens) > 1 and title_overlap == len(title_tokens) - 1:
            score += 30

    if author_tokens:
        score += author_overlap * 10
        if author_overlap == len(author_tokens):
            score += 25

    requested_edition_number = extract_edition_number(requested_edition)
    candidate_edition_number = extract_edition_number(" ".join([candidate_title, candidate_edition_text]))
    if requested_edition_number is not None:
        if candidate_edition_number == requested_edition_number:
            score += 120
        elif candidate_edition_number is not None:
            score -= 180

    title_ratio = (title_overlap / len(title_tokens)) if title_tokens else 0.0
    return {
        "score": score,
        "title_overlap": title_overlap,
        "author_overlap": author_overlap,
        "title_ratio": title_ratio,
        "requested_title_token_count": len(title_tokens),
        "requested_author_token_count": len(author_tokens),
        "requested_edition_number": requested_edition_number,
        "candidate_edition_number": candidate_edition_number,
        "isbn_matched": bool(requested_isbn and requested_isbn in candidate_isbns),
    }


def is_reasonable_provider_match(requested_book: Dict[str, str], score_details: Dict[str, Any]) -> bool:
    if score_details.get("isbn_matched"):
        return True

    title_token_count = score_details.get("requested_title_token_count", 0)
    title_overlap = score_details.get("title_overlap", 0)
    author_token_count = score_details.get("requested_author_token_count", 0)
    author_overlap = score_details.get("author_overlap", 0)
    requested_edition_number = score_details.get("requested_edition_number")
    candidate_edition_number = score_details.get("candidate_edition_number")

    if title_token_count == 0:
        return False

    minimum_title_overlap = max(1, min(title_token_count, 2))
    if title_overlap < minimum_title_overlap:
        return False

    if title_token_count >= 3 and score_details.get("title_ratio", 0.0) < 0.6:
        return False

    if author_token_count > 0 and author_overlap == 0 and title_token_count >= 2:
        return False

    if requested_edition_number is not None and candidate_edition_number is not None and requested_edition_number != candidate_edition_number:
        return False

    return score_details.get("score", 0) >= 30


def select_best_provider_candidate(
    requested_book: Dict[str, str],
    candidates: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    best_candidate = None
    best_score = None
    for candidate in candidates:
        score_details = score_provider_candidate(
            requested_book=requested_book,
            candidate_title=candidate.get("candidate_title", ""),
            candidate_authors=candidate.get("candidate_authors", []),
            candidate_edition_text=candidate.get("candidate_edition_text", ""),
            candidate_isbns=candidate.get("candidate_isbns", []),
        )
        if not is_reasonable_provider_match(requested_book, score_details):
            continue
        if best_score is None or score_details["score"] > best_score:
            best_candidate = {**candidate, "match_score": score_details["score"]}
            best_score = score_details["score"]
    return best_candidate

@app.get("/book")
async def search_book(
    title: str = Query(..., description="Tên sách cần tìm"),
    per_page: int = Query(5, ge=1, le=20, description="Số kết quả trả về (1-20)")
):
    """
    Tìm kiếm sách theo tên sử dụng OpenAlex API.
    Kết quả trả về danh sách các sách với thông tin cơ bản.
    """
    # Xây dựng bộ lọc: tìm kiếm trong tiêu đề, chỉ lấy sách (type:book)
    filters = f"title.search:{title},type:book"
    
    params = {
        "api_key": OPENALEX_API_KEY,
        "filter": filters,
        "per-page": per_page,
        "select": "id,title,authors,publication_year,doi,url"  # chỉ lấy các trường cần thiết
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(BASE_URL, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Lỗi từ OpenAlex: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Không thể kết nối tới OpenAlex: {str(e)}"
            )

    data = response.json()
    results = data.get("results", [])
    
    # Định dạng lại kết quả gọn gàng
    formatted = []
    for work in results:
        authors = [author.get("author", {}).get("display_name", "Unknown") 
                   for author in work.get("authorships", [])]
        formatted.append({
            "id": work.get("id"),
            "title": work.get("title"),
            "authors": authors,
            "year": work.get("publication_year"),
            "doi": work.get("doi"),
            "openalex_url": work.get("url")
        })
    
    return {
        "query": title,
        "count": len(formatted),
        "results": formatted
    }

@app.get("/search_books", response_model=Dict[str, Any])
async def search_books(
    q: str = Query(..., description="Book title or search query"),
    limit: int = Query(10, ge=1, le=100, description="Number of results to return"),
    fields: Optional[str] = Query(
        None,
        description="Comma-separated fields to return (e.g., 'title,author_name,isbn')"
    ),
    lang: Optional[str] = Query(None, description="Two-letter language code (e.g., 'en')"),
    sort: Optional[str] = Query(None, description="Sort order (e.g., 'new', 'old')")
):
    """
    Endpoint 1: Search for books by name using the Open Library Search API.
    """
    default_fields = ["key", "title", "author_name", "first_publish_year", "isbn"]
    requested_fields = [field.strip() for field in fields.split(",")] if fields else []
    merged_fields = []

    for field in default_fields + requested_fields:
        if field and field not in merged_fields:
            merged_fields.append(field)

    params: Dict[str, Any] = {
        "q": q,
        "limit": limit,
        "fields": ",".join(merged_fields),
    }
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

    normalized_results = []
    for doc in data.get("docs", []):
        isbns = doc.get("isbn") or []
        normalized_doc = dict(doc)
        normalized_doc["isbn"] = isbns
        normalized_doc["primary_isbn"] = isbns[0] if isbns else None
        normalized_results.append(normalized_doc)

    return {
        "query": q,
        "total_results": data.get("num_found", 0),
        "results": normalized_results
    }


async def search_openlibrary_first_result(book_or_title: Any) -> Optional[Dict[str, Any]]:
    """Return the best Open Library match for a requested book."""
    requested_book = build_book_lookup_request(book_or_title)
    default_fields = ["key", "title", "author_name", "first_publish_year", "isbn"]
    params: Dict[str, Any] = {
        "title": requested_book["title"],
        "limit": 10,
        "fields": ",".join(default_fields),
    }
    if requested_book["author"]:
        params["author"] = requested_book["author"]
    if requested_book["isbn"]:
        params["isbn"] = requested_book["isbn"]

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(OPEN_LIBRARY_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    docs = data.get("docs", [])
    if not docs:
        return None

    candidates = []
    for raw_doc in docs:
        doc = dict(raw_doc)
        candidates.append(
            {
                "candidate_title": doc.get("title", ""),
                "candidate_authors": doc.get("author_name") or [],
                "candidate_edition_text": "",
                "candidate_isbns": doc.get("isbn") or [],
                "doc": doc,
            }
        )

    best_match = select_best_provider_candidate(requested_book, candidates)
    if not best_match:
        return None

    doc = dict(best_match["doc"])
    isbns = doc.get("isbn") or []
    work_key = doc.get("key")
    primary_isbn = isbns[0] if isbns else None

    doc["isbn"] = isbns
    doc["primary_isbn"] = primary_isbn
    doc["provider"] = "openlibrary"
    doc["provider_link"] = (
        f"{OPEN_LIBRARY_WORK_URL}{work_key}" if work_key else (
            f"{OPEN_LIBRARY_BOOK_URL}/{primary_isbn}" if primary_isbn else OPEN_LIBRARY_SEARCH_URL
        )
    )
    doc["provider_book_id"] = work_key
    doc["query_api"] = OPEN_LIBRARY_SEARCH_URL
    return doc


async def search_google_books_first_result(book_or_title: Any) -> Optional[Dict[str, Any]]:
    requested_book = build_book_lookup_request(book_or_title)
    query_parts = [f'intitle:"{requested_book["title"]}"']
    if requested_book["author"]:
        query_parts.append(f'inauthor:"{requested_book["author"]}"')
    if requested_book["isbn"]:
        query_parts.append(f'isbn:{requested_book["isbn"]}')
    params: Dict[str, Any] = {
        "q": " ".join(query_parts),
        "maxResults": 10,
        "printType": "books",
    }
    if GOOGLE_BOOKS_API_KEY:
        params["key"] = GOOGLE_BOOKS_API_KEY

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(GOOGLE_BOOKS_VOLUMES_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    items = data.get("items", [])
    if not items:
        return None

    candidates = []
    for volume in items:
        volume_info = volume.get("volumeInfo", {})
        industry_ids = volume_info.get("industryIdentifiers", [])
        isbn_candidates = [entry.get("identifier") for entry in industry_ids if entry.get("identifier")]
        candidates.append(
            {
                "candidate_title": volume_info.get("title", ""),
                "candidate_authors": volume_info.get("authors", []),
                "candidate_edition_text": volume_info.get("subtitle", ""),
                "candidate_isbns": isbn_candidates,
                "volume": volume,
            }
        )

    best_match = select_best_provider_candidate(requested_book, candidates)
    if not best_match:
        return None

    volume = best_match["volume"]
    volume_info = volume.get("volumeInfo", {})
    industry_ids = volume_info.get("industryIdentifiers", [])
    isbn_candidates = [entry.get("identifier") for entry in industry_ids if entry.get("identifier")]
    return {
        "title": volume_info.get("title", requested_book["title"]),
        "author_name": volume_info.get("authors", []),
        "primary_isbn": isbn_candidates[0] if isbn_candidates else None,
        "provider": "google_books",
        "provider_book_id": volume.get("id"),
        "provider_link": volume_info.get("infoLink") or volume_info.get("previewLink"),
        "query_api": GOOGLE_BOOKS_VOLUMES_URL,
        "raw_result": volume,
    }


async def search_internet_archive_first_result(book_or_title: Any) -> Optional[Dict[str, Any]]:
    requested_book = build_book_lookup_request(book_or_title)
    query = f'title:("{requested_book["title"]}") AND mediatype:texts'
    if requested_book["author"]:
        query += f' AND creator:("{requested_book["author"]}")'
    params = {
        "q": query,
        "fl[]": ["identifier", "title", "creator", "year"],
        "rows": 10,
        "page": 1,
        "output": "json",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(INTERNET_ARCHIVE_ADVANCED_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    docs = data.get("response", {}).get("docs", [])
    if not docs:
        return None

    candidates = []
    for doc in docs:
        creator = doc.get("creator")
        creators = creator if isinstance(creator, list) else ([creator] if creator else [])
        candidates.append(
            {
                "candidate_title": doc.get("title", ""),
                "candidate_authors": creators,
                "candidate_edition_text": "",
                "candidate_isbns": [],
                "doc": doc,
            }
        )

    best_match = select_best_provider_candidate(requested_book, candidates)
    if not best_match:
        return None

    doc = best_match["doc"]
    identifier = doc.get("identifier")
    creator = doc.get("creator")
    creators = creator if isinstance(creator, list) else ([creator] if creator else [])
    return {
        "title": doc.get("title", requested_book["title"]),
        "author_name": creators,
        "provider": "internet_archive",
        "provider_book_id": identifier,
        "provider_link": f"https://archive.org/details/{identifier}" if identifier else None,
        "query_api": INTERNET_ARCHIVE_ADVANCED_SEARCH_URL,
        "raw_result": doc,
    }


async def search_hathitrust_first_result(book_or_title: Any) -> Optional[Dict[str, Any]]:
    requested_book = build_book_lookup_request(book_or_title)
    isbn = requested_book["isbn"] or await get_isbn_from_title(requested_book["title"])
    if not isbn:
        return None

    endpoint = f"{HATHITRUST_ISBN_API_URL}/{isbn}.json"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(endpoint)
        resp.raise_for_status()
        data = resp.json()

    records = data.get("records", {})
    if not records:
        return None

    record = next(iter(records.values()))
    return {
        "title": record.get("titles", [{}])[0].get("title", requested_book["title"]) if record.get("titles") else requested_book["title"],
        "author_name": [author.get("name") for author in record.get("authors", []) if author.get("name")],
        "primary_isbn": isbn,
        "provider": "hathitrust",
        "provider_book_id": record.get("recordURL"),
        "provider_link": record.get("recordURL"),
        "query_api": endpoint,
        "raw_result": record,
    }


async def search_worldcat_first_result(book_or_title: Any) -> Optional[Dict[str, Any]]:
    if not WORLDCAT_API_KEY:
        return None

    requested_book = build_book_lookup_request(book_or_title)
    headers = {"Authorization": f"Bearer {WORLDCAT_API_KEY}", "Accept": "application/json"}
    query_parts = [f'ti:"{requested_book["title"]}"']
    if requested_book["author"]:
        query_parts.append(f'au:"{requested_book["author"]}"')
    if requested_book["isbn"]:
        query_parts.append(f'isbn:{requested_book["isbn"]}')
    params = {"q": " AND ".join(query_parts), "limit": 10}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(WORLDCAT_SEARCH_V2_URL, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    brief_records = data.get("briefRecords", [])
    if not brief_records:
        return None

    candidates = []
    for record in brief_records:
        candidates.append(
            {
                "candidate_title": record.get("title", ""),
                "candidate_authors": [record.get("creator")] if record.get("creator") else [],
                "candidate_edition_text": record.get("edition", ""),
                "candidate_isbns": record.get("isbns") or [],
                "record": record,
            }
        )

    best_match = select_best_provider_candidate(requested_book, candidates)
    if not best_match:
        return None

    record = best_match["record"]
    return {
        "title": record.get("title", requested_book["title"]),
        "author_name": [record.get("creator")] if record.get("creator") else [],
        "provider": "worldcat",
        "provider_book_id": record.get("oclcNumber"),
        "provider_link": record.get("catalogUrl"),
        "query_api": WORLDCAT_SEARCH_V2_URL,
        "raw_result": record,
    }


async def search_doab_first_result(book_or_title: Any) -> Optional[Dict[str, Any]]:
    requested_book = build_book_lookup_request(book_or_title)
    params = {"lookfor": requested_book["title"], "type": "AllFields", "limit": 10}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(DOAB_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    results = data.get("records", []) if isinstance(data, dict) else []
    if not results:
        return None

    candidates = []
    for record in results:
        authors = record.get("authors", [])
        if isinstance(authors, str):
            authors = [authors]
        candidates.append(
            {
                "candidate_title": record.get("title", ""),
                "candidate_authors": authors,
                "candidate_edition_text": "",
                "candidate_isbns": [],
                "record": record,
            }
        )

    best_match = select_best_provider_candidate(requested_book, candidates)
    if not best_match:
        return None

    record = best_match["record"]
    return {
        "title": record.get("title", requested_book["title"]),
        "author_name": record.get("authors", []),
        "provider": "doab",
        "provider_book_id": record.get("id"),
        "provider_link": record.get("url"),
        "query_api": DOAB_SEARCH_URL,
        "raw_result": record,
    }


async def search_oapen_first_result(book_or_title: Any) -> Optional[Dict[str, Any]]:
    requested_book = build_book_lookup_request(book_or_title)
    params = {"query": requested_book["title"], "size": 10}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(OAPEN_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    results = data.get("results", []) if isinstance(data, dict) else []
    if not results:
        return None

    candidates = []
    for record in results:
        creators = record.get("creators", [])
        if isinstance(creators, str):
            creators = [creators]
        candidates.append(
            {
                "candidate_title": record.get("title", ""),
                "candidate_authors": creators,
                "candidate_edition_text": "",
                "candidate_isbns": [],
                "record": record,
            }
        )

    best_match = select_best_provider_candidate(requested_book, candidates)
    if not best_match:
        return None

    record = best_match["record"]
    return {
        "title": record.get("title", requested_book["title"]),
        "author_name": record.get("creators", []),
        "provider": "oapen",
        "provider_book_id": record.get("id"),
        "provider_link": record.get("url"),
        "query_api": OAPEN_SEARCH_URL,
        "raw_result": record,
    }


async def search_primo_first_result(book_or_title: Any) -> Optional[Dict[str, Any]]:
    if not PRIMO_API_KEY or not PRIMO_BASE_URL or not PRIMO_VIEW:
        return None

    requested_book = build_book_lookup_request(book_or_title)
    params = {
        "vid": PRIMO_VIEW,
        "q": f'any,contains,{requested_book["title"]}',
        "limit": 10,
        "apikey": PRIMO_API_KEY,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{PRIMO_BASE_URL.rstrip('/')}/primo/v1/search", params=params)
        resp.raise_for_status()
        data = resp.json()

    docs = data.get("docs", [])
    if not docs:
        return None

    candidates = []
    for record in docs:
        pnx = record.get("pnx", {})
        display = pnx.get("display", {})
        title_value = (display.get("title") or [requested_book["title"]])[0] if isinstance(display.get("title"), list) else display.get("title", requested_book["title"])
        creators = display.get("creator", [])
        if isinstance(creators, str):
            creators = [creators]
        candidates.append(
            {
                "candidate_title": title_value,
                "candidate_authors": creators,
                "candidate_edition_text": "",
                "candidate_isbns": [],
                "record": record,
            }
        )

    best_match = select_best_provider_candidate(requested_book, candidates)
    if not best_match:
        return None

    record = best_match["record"]
    pnx = record.get("pnx", {})
    display = pnx.get("display", {})
    links = pnx.get("links", {})
    linktohtml = links.get("linktorsrc") or []
    first_link = linktohtml[0] if linktohtml else None
    return {
        "title": (display.get("title") or [requested_book["title"]])[0] if isinstance(display.get("title"), list) else display.get("title", requested_book["title"]),
        "author_name": display.get("creator", []),
        "provider": "primo",
        "provider_book_id": record.get("pnx", {}).get("control", {}).get("recordid"),
        "provider_link": first_link,
        "query_api": f"{PRIMO_BASE_URL.rstrip('/')}/primo/v1/search",
        "raw_result": record,
    }


async def search_eds_first_result(book_or_title: Any) -> Optional[Dict[str, Any]]:
    if not EDS_PROFILE or not EDS_API_TOKEN:
        return None

    requested_book = build_book_lookup_request(book_or_title)
    headers = {
        "x-sessionToken": EDS_API_TOKEN,
        "Accept": "application/json",
    }
    params = {"query": requested_book["title"], "profile": EDS_PROFILE, "resultsperpage": 10}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(EDS_BASE_URL, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    records = data.get("SearchResult", {}).get("Data", {}).get("Records", [])
    if not records:
        return None

    candidates = []
    for record in records:
        items = record.get("Items", [])
        title_value = next((item.get("Data") for item in items if item.get("Name") == "Title"), requested_book["title"])
        author_value = next((item.get("Data") for item in items if item.get("Name") in {"Author", "Authors"}), "")
        authors = author_value if isinstance(author_value, list) else ([author_value] if author_value else [])
        candidates.append(
            {
                "candidate_title": title_value,
                "candidate_authors": authors,
                "candidate_edition_text": "",
                "candidate_isbns": [],
                "record": record,
            }
        )

    best_match = select_best_provider_candidate(requested_book, candidates)
    if not best_match:
        return None

    record = best_match["record"]
    items = record.get("Items", [])
    title_value = next((item.get("Data") for item in items if item.get("Name") == "Title"), requested_book["title"])
    return {
        "title": title_value,
        "author_name": [],
        "provider": "eds",
        "provider_book_id": record.get("Header", {}).get("DbId"),
        "provider_link": None,
        "query_api": EDS_BASE_URL,
        "raw_result": record,
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
        def find_first(element: ET.Element, paths: List[str], namespaces: Dict[str, str]) -> Optional[ET.Element]:
            for path in paths:
                match = element.find(path, namespaces)
                if match is not None:
                    return match
            return None

        def parse_optional_float(element: Optional[ET.Element]) -> Optional[float]:
            if element is None or element.text is None or not element.text.strip():
                return None
            return float(element.text.strip())

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

        result_elem = find_first(
            resp,
            ['.//ns:GetTextbookXInfoResult', './/GetTextbookXInfoResult'],
            namespaces
        ) or resp

        ebook_price_elem = find_first(result_elem, ['.//ns:EBookPrice', './/EBookPrice'], namespaces)
        used_price_elem = find_first(result_elem, ['.//ns:UsedPrice', './/UsedPrice'], namespaces)
        new_price_elem = find_first(result_elem, ['.//ns:NewPrice', './/NewPrice'], namespaces)
        ebook_url_elem = find_first(result_elem, ['.//ns:EBookBuyUrl', './/EBookBuyUrl'], namespaces)
        used_url_elem = find_first(result_elem, ['.//ns:UsedBuyUrl', './/UsedBuyUrl'], namespaces)
        new_url_elem = find_first(result_elem, ['.//ns:NewBuyUrl', './/NewBuyUrl'], namespaces)
        error_elem = find_first(result_elem, ['.//ns:ErrorMsg', './/ErrorMsg'], namespaces)

        if ebook_price_elem is None and used_price_elem is None and new_price_elem is None:
            raise ValueError("Missing price fields in response")

        return {
            "new_price": parse_optional_float(new_price_elem),
            "used_price": parse_optional_float(used_price_elem),
            "ebook_price": parse_optional_float(ebook_price_elem),
            "new_url": new_url_elem.text.strip() if new_url_elem is not None and new_url_elem.text else None,
            "used_url": used_url_elem.text.strip() if used_url_elem is not None and used_url_elem.text else None,
            "ebook_url": ebook_url_elem.text.strip() if ebook_url_elem is not None and ebook_url_elem.text else None,
            "error_message": error_elem.text.strip() if error_elem is not None and error_elem.text else None,
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
async def resolve_book_reference(book: Dict[str, Any]) -> Dict[str, Any]:
    requested_title = book.get("bookname", "")
    requested_author = book.get("author", "")
    requested_edition = book.get("edition", "")
    requested_isbn = extract_first_isbn(book.get("isbn", ""))

    if requested_isbn:
        return {"isbn": requested_isbn, "edition_warning": None, "match_source": "syllabus_isbn"}

    params: Dict[str, Any] = {
        "title": requested_title,
        "author": requested_author,
        "limit": 5,
        "fields": "key,title,author_name,isbn",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(OPEN_LIBRARY_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    docs = data.get("docs", [])
    if not docs:
        return {"isbn": None, "edition_warning": "No matching textbook candidates were found.", "match_source": "not_found"}

    best_match = None
    best_score = -10**9
    best_entry = None
    best_work_key = None

    async with httpx.AsyncClient(timeout=10.0) as client:
        for doc in docs:
            work_key = doc.get("key")
            if not work_key:
                continue
            editions_url = f"https://openlibrary.org{work_key}/editions.json"
            resp = await client.get(editions_url, params={"limit": 30})
            resp.raise_for_status()
            editions_data = resp.json()
            for entry in editions_data.get("entries", []):
                score = score_openlibrary_edition_candidate(
                    entry=entry,
                    requested_title=requested_title,
                    requested_author=requested_author,
                    requested_edition=requested_edition,
                    requested_isbn=requested_isbn,
                )
                if score > best_score:
                    best_score = score
                    best_entry = entry
                    best_work_key = work_key

    if not best_entry:
        primary_isbn = docs[0].get("primary_isbn") or (docs[0].get("isbn") or [None])[0]
        return {"isbn": primary_isbn, "edition_warning": "Edition could not be verified from provider data.", "match_source": "search_fallback"}

    matched_isbn = None
    if best_entry.get("isbn_13"):
        matched_isbn = best_entry["isbn_13"][0]
    elif best_entry.get("isbn_10"):
        matched_isbn = best_entry["isbn_10"][0]

    edition_warning = build_edition_warning(requested_edition, best_entry)

    return {
        "isbn": matched_isbn,
        "edition_warning": edition_warning,
        "match_source": "ranked_candidates",
        "work_key": best_work_key,
    }


async def get_isbn_from_title(title: str) -> Optional[str]:
    resolved = await resolve_book_reference({"bookname": title, "author": "", "edition": "", "year": "", "isbn": ""})
    return resolved.get("isbn")

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


async def search_ecampus_for_book(book: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    resolved = await resolve_book_reference(book)
    isbn = resolved.get("isbn")
    if not isbn:
        return None

    return {
        "title": book.get("bookname", ""),
        "isbn": isbn,
        "primary_isbn": isbn,
        "provider": "ecampus",
        "provider_book_id": isbn,
        "provider_link": None,
        "query_api": "/search_ecampus",
        "edition_warning": resolved.get("edition_warning"),
        "match_source": resolved.get("match_source"),
    }


async def search_ecampus_first_result(title: str) -> Optional[Dict[str, Any]]:
    """Return the first eCampus candidate for a title using Open Library ISBN discovery."""
    return await search_ecampus_for_book({"bookname": title, "author": "", "edition": "", "year": "", "isbn": ""})

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


def get_lowest_price(pricing: Dict[str, Any]) -> Optional[float]:
    prices = [
        pricing.get("ebook_price"),
        pricing.get("used_price"),
        pricing.get("new_price"),
    ]
    valid_prices = [price for price in prices if isinstance(price, (int, float)) and price >= 0]
    return min(valid_prices) if valid_prices else None


def get_lowest_price_label(pricing: Dict[str, Any]) -> Optional[str]:
    options = {
        "ebook": pricing.get("ebook_price"),
        "used": pricing.get("used_price"),
        "new": pricing.get("new_price"),
    }
    valid_options = {
        label: price for label, price in options.items()
        if isinstance(price, (int, float)) and price >= 0
    }
    if not valid_options:
        return None
    return min(valid_options, key=valid_options.get)


def get_price_url_for_type(pricing: Dict[str, Any], price_type: Optional[str]) -> Optional[str]:
    url_map = {
        "ebook": pricing.get("ebook_url"),
        "used": pricing.get("used_url"),
        "new": pricing.get("new_url"),
    }
    if price_type and url_map.get(price_type):
        return url_map[price_type]

    for fallback in ["used", "ebook", "new"]:
        if url_map.get(fallback):
            return url_map[fallback]
    return None


def get_openlibrary_cost(availability: Dict[str, Any]) -> Optional[float]:
    if not availability:
        return None

    if availability.get("is_readable") or availability.get("is_lendable") or availability.get("status") == "open":
        return 0.0

    return None


def is_actionable_provider_option(provider_detail: Dict[str, Any]) -> bool:
    acquisition_mode = provider_detail.get("acquisition_mode")
    estimated_cost = provider_detail.get("estimated_cost")
    provider_link = provider_detail.get("provider_link")

    if not isinstance(estimated_cost, (int, float)):
        return False

    if acquisition_mode == "borrow":
        return bool(provider_link) and estimated_cost >= 0

    if acquisition_mode == "buy":
        return bool(provider_link) and estimated_cost > 0

    return False


def sort_provider_options(provider_details: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def sort_key(item: Dict[str, Any]) -> Any:
        actionable_rank = 0 if is_actionable_provider_option(item) else 1
        estimated_cost = item.get("estimated_cost")
        numeric_cost = estimated_cost if isinstance(estimated_cost, (int, float)) else float("inf")
        has_link_rank = 0 if item.get("provider_link") else 1
        return (actionable_rank, numeric_cost, has_link_rank, item.get("provider", "zzzz"))

    return sorted(provider_details, key=sort_key)


async def gather_provider_comparison(title: str, book: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    search_results: List[Dict[str, Any]] = []
    provider_details: List[Dict[str, Any]] = []
    attempted_titles: List[str] = []
    book = book or {"bookname": title, "author": "", "edition": "", "year": "", "isbn": ""}

    candidate_titles = []
    for candidate in [book.get("bookname", title), normalize_book_lookup_title(book.get("bookname", title))]:
        candidate = (candidate or "").strip()
        if candidate and candidate not in candidate_titles:
            candidate_titles.append(candidate)

    for candidate_title in candidate_titles:
        attempted_titles.append(candidate_title)
        candidate_book = {**book, "bookname": candidate_title}
        provider_searches = [
            search_openlibrary_first_result(candidate_book),
            search_ecampus_for_book(candidate_book),
            search_google_books_first_result(candidate_book),
            search_internet_archive_first_result(candidate_book),
            search_hathitrust_first_result(candidate_book),
            search_worldcat_first_result(candidate_book),
            search_doab_first_result(candidate_book),
            search_oapen_first_result(candidate_book),
            search_primo_first_result(candidate_book),
            search_eds_first_result(candidate_book),
        ]
        discovered_results = await asyncio.gather(*provider_searches, return_exceptions=True)

        for result in discovered_results:
            if isinstance(result, Exception) or result is None:
                continue
            dedupe_key = f"{result.get('provider')}|{result.get('provider_book_id') or result.get('primary_isbn')}"
            if dedupe_key in {f"{item.get('provider')}|{item.get('provider_book_id') or item.get('primary_isbn')}" for item in search_results}:
                continue
            search_results.append(result)

        if search_results:
            break

    for search_result in search_results:
        provider = search_result.get("provider")
        isbn = search_result.get("primary_isbn") or search_result.get("isbn")
        provider_book_id = search_result.get("provider_book_id")

        detail_record: Dict[str, Any] = {
            "provider": provider,
            "provider_link": search_result.get("provider_link"),
            "query_api": search_result.get("query_api"),
            "provider_book_id": provider_book_id,
            "search_result": search_result,
        }

        try:
            if provider == "openlibrary":
                if not isbn:
                    detail_record["detail_error"] = "No ISBN available for Open Library detail lookup"
                else:
                    detail = await get_openlibrary_availability(str(isbn))
                    estimated_cost = get_openlibrary_cost(detail.get("availability") or {})
                    detail_record["detail_api"] = f"/pricing_openlibrary/{isbn}"
                    detail_record["detail"] = detail
                    detail_record["estimated_cost"] = estimated_cost
                    detail_record["acquisition_mode"] = "borrow"
            elif provider == "google_books":
                raw_result = search_result.get("raw_result", {})
                sale_info = raw_result.get("saleInfo", {})
                access_info = raw_result.get("accessInfo", {})
                list_price = sale_info.get("listPrice", {}).get("amount")
                buy_link = sale_info.get("buyLink")
                preview_link = raw_result.get("volumeInfo", {}).get("previewLink") or raw_result.get("volumeInfo", {}).get("infoLink")
                if isinstance(list_price, (int, float)) and buy_link:
                    detail_record["estimated_cost"] = float(list_price)
                    detail_record["acquisition_mode"] = "buy"
                    detail_record["price_type"] = "google_books"
                    detail_record["provider_link"] = buy_link
                elif access_info.get("viewability") in {"ALL_PAGES", "PARTIAL"} and preview_link:
                    detail_record["estimated_cost"] = 0.0
                    detail_record["acquisition_mode"] = "borrow"
                    detail_record["provider_link"] = preview_link
                detail_record["detail"] = raw_result
            elif provider == "internet_archive":
                detail_record["estimated_cost"] = 0.0
                detail_record["acquisition_mode"] = "borrow"
                detail_record["detail"] = search_result.get("raw_result", {})
            elif provider == "hathitrust":
                detail_record["estimated_cost"] = 0.0
                detail_record["acquisition_mode"] = "borrow"
                detail_record["detail"] = search_result.get("raw_result", {})
            elif provider == "ecampus":
                if not isbn:
                    detail_record["detail_error"] = "No ISBN available for eCampus pricing lookup"
                else:
                    detail = await get_ecampus_price(str(isbn))
                    estimated_cost = get_lowest_price(detail)
                    lowest_price_label = get_lowest_price_label(detail)
                    best_buy_url = get_price_url_for_type(detail, lowest_price_label)
                    detail_record["detail_api"] = f"/pricing/{isbn}"
                    detail_record["detail"] = {
                        "isbn": str(isbn),
                        **detail,
                    }
                    detail_record["estimated_cost"] = estimated_cost
                    detail_record["acquisition_mode"] = "buy"
                    detail_record["price_type"] = lowest_price_label
                    detail_record["provider_link"] = best_buy_url
                    if best_buy_url is None:
                        detail_record["detail_warning"] = "eCampus returned pricing but no direct textbook purchase URL."
            elif provider in {"doab", "oapen", "worldcat", "primo", "eds"}:
                detail_record["estimated_cost"] = 0.0
                detail_record["acquisition_mode"] = "borrow"
                detail_record["detail"] = search_result.get("raw_result", {})
        except httpx.HTTPStatusError as exc:
            detail_record["detail_error"] = f"Provider HTTP error: {exc.response.status_code}"
        except Exception as exc:
            detail_record["detail_error"] = str(exc)

        detail_record["is_actionable"] = is_actionable_provider_option(detail_record)
        provider_details.append(detail_record)

    provider_details = sort_provider_options(provider_details)

    comparable_results = [
        item for item in provider_details
        if is_actionable_provider_option(item)
    ]
    best_provider = min(comparable_results, key=lambda item: item["estimated_cost"]) if comparable_results else None

    return {
        "title": title,
        "attempted_titles": attempted_titles,
        "search_results": search_results,
        "provider_details": provider_details,
        "best_provider": best_provider,
    }


def summarize_acquisition_decision(
    periods: List[Dict[str, Any]],
    provider_comparison: Dict[str, Any],
) -> Dict[str, Any]:
    total_days = 0
    for period in periods:
        start_date = period.get("start_date")
        end_date = period.get("end_date")
        if not start_date or not end_date:
            continue
        total_days += (dt.date.fromisoformat(end_date) - dt.date.fromisoformat(start_date)).days + 1

    provider_options = sort_provider_options(provider_comparison.get("provider_details", []))
    best_provider = provider_comparison.get("best_provider")
    edition_warnings = [
        item.get("search_result", {}).get("edition_warning")
        for item in provider_options
        if item.get("search_result", {}).get("edition_warning")
    ]
    if not best_provider:
        fallback_link_option = next((item for item in provider_options if item.get("provider_link")), None)
        available_providers = [
            item.get("provider") for item in provider_options
            if item.get("provider")
        ]
        provider_text = ", ".join(available_providers) if available_providers else "the connected providers"
        if fallback_link_option:
            fallback_provider = fallback_link_option.get("provider")
            return {
                "recommended_action": fallback_link_option.get("acquisition_mode"),
                "recommended_duration_days": total_days,
                "best_provider": fallback_link_option,
                "provider_options": provider_options,
                "recommendation_reason": (
                    f"No priced actionable option was available, so the best linked access option from {fallback_provider} "
                    "is shown instead."
                ),
                "selected_link": fallback_link_option.get("provider_link"),
                "edition_warning": edition_warnings[0] if edition_warnings else None,
            }
        return {
            "recommended_action": None,
            "recommended_duration_days": total_days,
            "best_provider": None,
            "provider_options": provider_options,
            "recommendation_reason": f"No actionable option is currently available from {provider_text}.",
            "selected_link": None,
            "edition_warning": edition_warnings[0] if edition_warnings else None,
        }

    acquisition_mode = best_provider.get("acquisition_mode")
    estimated_cost = best_provider.get("estimated_cost")
    provider_name = best_provider.get("provider")
    price_type = best_provider.get("price_type")
    compared_provider_names = ", ".join(
        item.get("provider") for item in provider_options if item.get("provider")
    )
    if acquisition_mode == "borrow":
        recommendation_reason = (
            f"Compared providers: {compared_provider_names}. Use {provider_name} for about {total_days} day(s); it is currently the lowest-cost option "
            f"with an estimated cost of {estimated_cost}."
        )
    else:
        purchase_label = f"{price_type} copy" if price_type else "copy"
        direct_link_note = ""
        if not best_provider.get("provider_link"):
            direct_link_note = " Pricing is available, but no direct textbook link was returned."
        recommendation_reason = (
            f"Compared providers: {compared_provider_names}. Buy the {purchase_label} from {provider_name}; for the needed {total_days} day(s), it is currently the lowest-cost option "
            f"with an estimated cost of {estimated_cost}.{direct_link_note}"
        )

    return {
        "recommended_action": acquisition_mode,
        "recommended_duration_days": total_days,
        "best_provider": best_provider,
        "provider_options": provider_options,
        "recommendation_reason": recommendation_reason,
        "selected_link": best_provider.get("provider_link"),
        "edition_warning": best_provider.get("search_result", {}).get("edition_warning") or (edition_warnings[0] if edition_warnings else None),
    }


@app.get("/compare_book_providers", response_model=Dict[str, Any])
async def compare_book_providers(
    title: str = Query(..., description="Book title to compare across providers")
):
    """
    Search all provider query APIs, attach source metadata to the first result from each,
    then fetch provider-specific details and return the lowest-cost provider.
    """
    comparison = await gather_provider_comparison(title)
    if not comparison["search_results"]:
        raise HTTPException(status_code=404, detail="No providers returned a match for this book title")
    return comparison

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
        "isbn": {"type": "string"},
    },
    "required": ["bookname", "author", "edition", "year", "isbn"],
    "additionalProperties": False,
}

SCHEDULE_ITEM_TYPE_ENUM = [
    "exam",
    "quiz",
    "homework",
    "assignment",
    "reading",
    "lecture",
    "deadline",
    "project",
    "other",
]

BOOK_EXTRACTION_SCHEMA: Dict[str, Any] = {
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

BOOK_HINT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "title_hint": {"type": "string"},
        "author_hint": {"type": "string"},
    },
    "required": ["title_hint", "author_hint"],
    "additionalProperties": False,
}

SCHEDULE_ITEM_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "item_type": {"type": "string", "enum": SCHEDULE_ITEM_TYPE_ENUM},
        "label": {"type": "string"},
        "raw_date_text": {"type": "string"},
        "start_date": {"type": "string"},
        "end_date": {"type": "string"},
        "week_label": {"type": "string"},
        "source_snippet": {"type": "string"},
        "confidence": {"type": "number"},
        "is_estimated": {"type": "boolean"},
        "book_hint": BOOK_HINT_SCHEMA,
    },
    "required": [
        "item_type",
        "label",
        "raw_date_text",
        "start_date",
        "end_date",
        "week_label",
        "source_snippet",
        "confidence",
        "is_estimated",
        "book_hint",
    ],
    "additionalProperties": False,
}

COURSE_CALENDAR_CONTEXT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "course_start_date": {"type": "string"},
        "course_end_date": {"type": "string"},
        "term_label": {"type": "string"},
        "date_anchor_notes": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["course_start_date", "course_end_date", "term_label", "date_anchor_notes"],
    "additionalProperties": False,
}

BOOK_CHAPTER_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "bookname": {"type": "string"},
        "author": {"type": "string"},
        "chapter_focuses": {
            "type": "array",
            "items": {"type": "string"},
        },
        "topic_focuses": {
            "type": "array",
            "items": {"type": "string"},
        },
        "notes": {"type": "string"},
    },
    "required": ["bookname", "author", "chapter_focuses", "topic_focuses", "notes"],
    "additionalProperties": False,
}

SYLLABUS_ANALYSIS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "books": {
            "type": "array",
            "items": BOOK_SCHEMA,
        },
        "schedule_items": {
            "type": "array",
            "items": SCHEDULE_ITEM_SCHEMA,
        },
        "course_calendar_context": COURSE_CALENDAR_CONTEXT_SCHEMA,
        "book_chapters": {
            "type": "array",
            "items": BOOK_CHAPTER_SCHEMA,
        },
    },
    "required": ["books", "schedule_items", "course_calendar_context", "book_chapters"],
    "additionalProperties": False,
}


class BookInfo(BaseModel):
    bookname: str
    author: str
    edition: str
    year: str
    isbn: str


class BookHint(BaseModel):
    title_hint: str
    author_hint: str


class ScheduleItemInfo(BaseModel):
    item_type: str
    label: str
    raw_date_text: str
    start_date: str
    end_date: str
    week_label: str
    source_snippet: str
    confidence: float
    is_estimated: bool
    book_hint: BookHint


class CourseCalendarContextInfo(BaseModel):
    course_start_date: str
    course_end_date: str
    term_label: str
    date_anchor_notes: List[str]


class BookChapterInfo(BaseModel):
    bookname: str
    author: str
    chapter_focuses: List[str]
    topic_focuses: List[str]
    notes: str


class SyllabusAnalysisInfo(BaseModel):
    books: List[BookInfo]
    schedule_items: List[ScheduleItemInfo]
    course_calendar_context: CourseCalendarContextInfo
    book_chapters: List[BookChapterInfo]


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


DATE_PATTERNS = [
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%m-%d-%Y",
    "%m-%d-%y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%B %d %Y",
    "%b %d %Y",
    "%B %d",
    "%b %d",
]
RELEVANT_RENTAL_TYPES = {"reading", "homework", "assignment", "quiz", "exam", "project", "deadline", "lecture", "other"}
WINDOW_START_BUFFER_DAYS = 7
WINDOW_END_BUFFER_DAYS = 2
WINDOW_MERGE_GAP_DAYS = 5


def try_parse_date(value: str, fallback_year: Optional[int] = None) -> Optional[dt.date]:
    cleaned = (value or "").strip()
    if not cleaned:
        return None

    normalized = re.sub(r"(?<=\d)(st|nd|rd|th)", "", cleaned, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", " ", normalized)

    for pattern in DATE_PATTERNS:
        try:
            if "%Y" in pattern:
                parsed = dt.datetime.strptime(normalized, pattern).date()
            else:
                parse_year = fallback_year if fallback_year is not None else 2000
                parsed = dt.datetime.strptime(f"{normalized} {parse_year}", f"{pattern} %Y").date()
                if fallback_year is None:
                    parsed = parsed.replace(year=parse_year)
            return parsed
        except ValueError:
            continue

    month_day_match = re.search(r"([A-Za-z]+)\s+(\d{1,2})\s*[-–]\s*(\d{1,2})(?:,?\s*(\d{4}))?", normalized)
    if month_day_match:
        start_text = f"{month_day_match.group(1)} {month_day_match.group(2)}"
        year = month_day_match.group(4)
        return try_parse_date(start_text, int(year) if year else fallback_year)

    numeric_match = re.search(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", normalized)
    if numeric_match:
        year = numeric_match.group(3)
        if year:
            year_value = int(year)
            if year_value < 100:
                year_value += 2000
            return dt.date(year_value, int(numeric_match.group(1)), int(numeric_match.group(2)))
        if fallback_year is not None:
            return dt.date(fallback_year, int(numeric_match.group(1)), int(numeric_match.group(2)))

    return None


def parse_date_range(raw_date_text: str, fallback_year: Optional[int] = None) -> Dict[str, Optional[str]]:
    raw = (raw_date_text or "").strip()
    if not raw:
        return {"start_date": None, "end_date": None}

    range_match = re.search(
        r"([A-Za-z]+\s+\d{1,2}|\d{1,2}/\d{1,2})(?:,?\s*(\d{4}))?\s*[-–]\s*(\d{1,2})",
        raw,
        flags=re.IGNORECASE,
    )
    if range_match:
        start_base = range_match.group(1)
        year_text = range_match.group(2)
        end_day = range_match.group(3)
        year_value = int(year_text) if year_text else fallback_year
        start_parsed = try_parse_date(
            f"{start_base}, {year_value}" if year_value and re.search(r"[A-Za-z]", start_base) else start_base,
            year_value,
        )
        if start_parsed:
            end_parsed = dt.date(start_parsed.year, start_parsed.month, int(end_day))
            return {"start_date": start_parsed.isoformat(), "end_date": end_parsed.isoformat()}

    single = try_parse_date(raw, fallback_year)
    if single:
        iso_date = single.isoformat()
        return {"start_date": iso_date, "end_date": iso_date}

    return {"start_date": None, "end_date": None}


def infer_known_years(schedule_items: List[Dict[str, Any]], context: Dict[str, Any]) -> List[int]:
    years = set()
    for candidate in [context.get("course_start_date"), context.get("course_end_date")]:
        parsed = try_parse_date(candidate or "")
        if parsed:
            years.add(parsed.year)

    for item in schedule_items:
        for field_name in ["start_date", "end_date"]:
            parsed = try_parse_date(item.get(field_name, ""))
            if parsed:
                years.add(parsed.year)
        raw_date_text = item.get("raw_date_text", "")
        explicit_year = re.search(r"\b(20\d{2})\b", raw_date_text)
        if explicit_year:
            years.add(int(explicit_year.group(1)))

    return sorted(years)


def extract_week_number(text: str) -> Optional[int]:
    match = re.search(r"week\s*(\d{1,2})", text or "", flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def resolve_schedule_dates(
    schedule_items: List[Dict[str, Any]],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    resolved_items: List[Dict[str, Any]] = []
    context_notes = list(context.get("date_anchor_notes") or [])
    known_years = infer_known_years(schedule_items, context)
    fallback_year = known_years[0] if known_years else None
    course_start = try_parse_date(context.get("course_start_date", ""), fallback_year)

    for item in schedule_items:
        normalized_item = dict(item)
        inference_notes = []

        start_date = try_parse_date(normalized_item.get("start_date", ""), fallback_year)
        end_date = try_parse_date(normalized_item.get("end_date", ""), fallback_year)

        if start_date is None and normalized_item.get("raw_date_text"):
            parsed_range = parse_date_range(normalized_item["raw_date_text"], fallback_year)
            if parsed_range["start_date"]:
                start_date = dt.date.fromisoformat(parsed_range["start_date"])
                end_date = dt.date.fromisoformat(parsed_range["end_date"] or parsed_range["start_date"])
                inference_notes.append("Normalized date from raw_date_text.")

        week_number = extract_week_number(normalized_item.get("week_label", "")) or extract_week_number(
            normalized_item.get("raw_date_text", "")
        )
        if start_date is None and week_number and course_start is not None:
            start_date = course_start + dt.timedelta(days=(week_number - 1) * 7)
            end_date = start_date
            normalized_item["is_estimated"] = True
            inference_notes.append(f"Inferred date from {normalized_item.get('week_label') or f'Week {week_number}'} and course_start_date.")

        if start_date and end_date is None:
            end_date = start_date

        normalized_item["start_date"] = start_date.isoformat() if start_date else ""
        normalized_item["end_date"] = end_date.isoformat() if end_date else ""
        normalized_item["date_inference_notes"] = inference_notes
        resolved_items.append(normalized_item)

    inferred_dates = [dt.date.fromisoformat(item["start_date"]) for item in resolved_items if item.get("start_date")]
    updated_context = dict(context)
    if not updated_context.get("course_start_date") and inferred_dates:
        updated_context["course_start_date"] = min(inferred_dates).isoformat()
        context_notes.append("Inferred course_start_date from earliest extracted schedule item.")
    if not updated_context.get("course_end_date") and inferred_dates:
        updated_context["course_end_date"] = max(inferred_dates).isoformat()
        context_notes.append("Inferred course_end_date from latest extracted schedule item.")
    updated_context["date_anchor_notes"] = context_notes

    return {
        "schedule_items": resolved_items,
        "course_calendar_context": updated_context,
    }

def match_schedule_item_to_book(item: Dict[str, Any], books: List[Dict[str, Any]]) -> Dict[str, Optional[Any]]:
    combined_text_parts = [
        item.get("label", ""),
        item.get("source_snippet", ""),
        item.get("raw_date_text", ""),
        item.get("book_hint", {}).get("title_hint", ""),
        item.get("book_hint", {}).get("author_hint", ""),
    ]
    combined_text = " ".join(combined_text_parts)
    combined_tokens = set(keyword_tokens(combined_text))

    best_book = None
    best_score = 0
    best_reason = None

    for book in books:
        score = 0
        reasons = []
        for token in keyword_tokens(book.get("bookname", "")):
            if token in combined_tokens:
                score += 3
                reasons.append(f"title token '{token}'")
        for token in keyword_tokens(book.get("author", "")):
            if token in combined_tokens:
                score += 2
                reasons.append(f"author token '{token}'")
        if book.get("edition") and normalize_text(book["edition"]) in normalize_text(combined_text):
            score += 1
            reasons.append("edition mention")

        if score > best_score:
            best_score = score
            best_book = book
            best_reason = ", ".join(reasons) if reasons else None

    if best_book is not None and best_score > 0:
        return {
            "book": best_book,
            "matching_reason": f"Heuristic match from {best_reason}.",
        }

    if len(books) == 1 and item.get("item_type") in RELEVANT_RENTAL_TYPES:
        return {
            "book": books[0],
            "matching_reason": "Single detected book fallback based on course timeline relevance.",
        }

    return {
        "book": None,
        "matching_reason": None,
    }


def build_book_timelines(books: List[Dict[str, Any]], schedule_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    timelines: Dict[str, Dict[str, Any]] = {
        book["bookname"]: {
            "book": book,
            "matched_schedule_items": [],
        }
        for book in books
    }

    for item in schedule_items:
        match = match_schedule_item_to_book(item, books)
        matched_book = match["book"]
        if matched_book is None:
            continue

        timelines[matched_book["bookname"]]["matched_schedule_items"].append({
            **item,
            "matching_reason": match["matching_reason"],
        })

    return list(timelines.values())


def merge_rental_windows(windows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not windows:
        return []

    sorted_windows = sorted(windows, key=lambda item: item["start_date"])
    merged = [sorted_windows[0]]

    for current in sorted_windows[1:]:
        previous = merged[-1]
        prev_end = dt.date.fromisoformat(previous["end_date"])
        curr_start = dt.date.fromisoformat(current["start_date"])

        if curr_start <= prev_end + dt.timedelta(days=WINDOW_MERGE_GAP_DAYS):
            previous["end_date"] = max(previous["end_date"], current["end_date"])
            previous["triggering_items"].extend(current["triggering_items"])
            previous["is_estimated"] = previous["is_estimated"] or current["is_estimated"]
        else:
            merged.append(current)

    deduped = []
    for item in merged:
        seen_labels = set()
        unique_triggers = []
        for trigger in item["triggering_items"]:
            trigger_key = f"{trigger.get('label')}|{trigger.get('start_date')}|{trigger.get('end_date')}"
            if trigger_key in seen_labels:
                continue
            seen_labels.add(trigger_key)
            unique_triggers.append(trigger)
        item["triggering_items"] = unique_triggers
        item["rental_reasoning"] = (
            "Rental window built from matched schedule items: "
            + ", ".join(trigger.get("label", "Untitled event") for trigger in unique_triggers)
        )
        deduped.append(item)

    return deduped


def build_rental_recommendations(book_timelines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    recommendations = []

    for timeline in book_timelines:
        windows = []
        for item in timeline["matched_schedule_items"]:
            item_type = item.get("item_type")
            if item_type not in RELEVANT_RENTAL_TYPES and not item.get("start_date"):
                continue
            if not item.get("start_date"):
                continue

            start_date = dt.date.fromisoformat(item["start_date"]) - dt.timedelta(days=WINDOW_START_BUFFER_DAYS)
            end_date = dt.date.fromisoformat(item.get("end_date") or item["start_date"]) + dt.timedelta(days=WINDOW_END_BUFFER_DAYS)
            windows.append({
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "is_estimated": bool(item.get("is_estimated")),
                "triggering_items": [{
                    "label": item.get("label"),
                    "item_type": item.get("item_type"),
                    "start_date": item.get("start_date"),
                    "end_date": item.get("end_date"),
                    "matching_reason": item.get("matching_reason"),
                }],
            })

        recommendations.append({
            "book": timeline["book"],
            "periods": merge_rental_windows(windows),
        })

    return recommendations


async def enrich_recommendations_with_provider_pricing(
    rental_recommendations: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    enriched_recommendations = []

    for recommendation in rental_recommendations:
        book = recommendation.get("book", {})
        book_title = book.get("bookname")
        if not book_title:
            enriched_recommendations.append(recommendation)
            continue

        provider_comparison = await gather_provider_comparison(book_title, book=book)
        enriched_recommendation = dict(recommendation)
        enriched_recommendation["pricing_recommendation"] = summarize_acquisition_decision(
            recommendation.get("periods", []),
            provider_comparison,
        )
        enriched_recommendations.append(enriched_recommendation)

    return enriched_recommendations


def call_openai_for_json(pdf_text: str) -> List[Dict[str, Any]]:
    """
    Send extracted PDF text to OpenAI and force structured JSON output.
    """
    if not pdf_text.strip():
        raise ValueError("No text could be extracted from the PDF.")

    response = client.responses.create(
        model="gpt-4o",
        input=[
            {
                "role": "system",
                "content": (
                    "You extract book mentions from document text and return only valid JSON. "
                    "Find every distinct book mentioned in the document. "
                    "Return a JSON object with a single key named 'books'. "
                    "The value of 'books' must be an array where each item contains exactly "
                    "these fields: bookname, author, edition, year, and isbn. "
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
                "schema": BOOK_EXTRACTION_SCHEMA,
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


def call_openai_for_syllabus_analysis(pdf_text: str) -> Dict[str, Any]:
    """
    Send extracted PDF text to OpenAI and return a structured syllabus analysis object.
    """
    if not pdf_text.strip():
        raise ValueError("No text could be extracted from the PDF.")

    response = client.responses.create(
        model="gpt-4o",
        input=[
            {
                "role": "system",
                "content": (
                    "You extract textbook and schedule information from a course syllabus and return only valid JSON. "
                    "Find every distinct required or recommended book. "
                    "Extract the book ISBN exactly when it appears in the syllabus. "
                    "Also extract all schedule-bearing events, especially exams, quizzes, homework, assignments, readings, lectures, projects, deadlines, and date markers. "
                    "At the same time, define the likely chapter focus and topic focus for each detected book based on the syllabus text. "
                    "Preserve raw date text exactly when possible. "
                    "Only provide normalized start_date or end_date when directly stated or strongly inferable from explicit syllabus context. "
                    "Use week_label for references like Week 3. "
                    "Include a short source_snippet for traceability and optional book_hint information with title_hint and author_hint when the event appears tied to a specific book. "
                    "Do not invent dates when the syllabus does not support them. "
                    "For each book_chapters entry, include chapter_focuses and topic_focuses as short lists. "
                    "If the syllabus does not explicitly give chapter numbers, use topic-based chapter focus descriptions and say so in notes. "
                    "Return a JSON object with keys books, schedule_items, course_calendar_context, and book_chapters, and no extra keys."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Analyze this syllabus.\n"
                    "Extract all books, all time-based schedule items, and the likely chapter/topic focus for each textbook. "
                    "If a field is unknown, use an empty string or false as appropriate.\n"
                    f"Document text:\n{pdf_text}"
                ),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "syllabus_analysis_result",
                "strict": True,
                "schema": SYLLABUS_ANALYSIS_SCHEMA,
            }
        },
    )

    try:
        parsed_json = json.loads(response.output_text)
        validated = SyllabusAnalysisInfo.model_validate(parsed_json).model_dump()
    except Exception as exc:
        raise ValueError(f"Failed to parse model output as valid syllabus analysis JSON: {exc}") from exc

    resolved = resolve_schedule_dates(
        validated["schedule_items"],
        validated["course_calendar_context"],
    )
    validated["schedule_items"] = resolved["schedule_items"]
    validated["course_calendar_context"] = resolved["course_calendar_context"]

    book_timelines = build_book_timelines(validated["books"], validated["schedule_items"])
    rental_recommendations = build_rental_recommendations(book_timelines)

    return {
        "books": validated["books"],
        "schedule_items": validated["schedule_items"],
        "book_timelines": book_timelines,
        "rental_recommendations": rental_recommendations,
        "course_calendar_context": validated["course_calendar_context"],
        "book_chapters": validated["book_chapters"],
    }


def build_study_planner_prompt(
    analysis: Dict[str, Any],
    user_context: StudyPlannerUserContext,
    user_message: str,
    chat_history: List[ChatMessage],
) -> List[Dict[str, str]]:
    books = analysis.get("books", [])
    timelines = analysis.get("book_timelines", [])
    rentals = analysis.get("rental_recommendations", [])

    compact_analysis = {
        "books": books,
        "book_chapters": analysis.get("book_chapters", []),
        "book_timelines": timelines,
        "rental_recommendations": rentals,
        "course_calendar_context": analysis.get("course_calendar_context", {}),
    }

    history_lines = []
    for message in chat_history[-8:]:
        history_lines.append(f"{message.role}: {message.content}")

    return [
        {
            "role": "system",
            "content": (
                "You are a textbook study-planning assistant. "
                "Your job is to personalize textbook usage for a student based on syllabus analysis and user context. "
                "Use the syllabus-derived books, schedule, and rental recommendations to answer. "
                "You should help the student identify what they likely need to study, how long they will need access to each textbook, "
                "what chapters or sections appear most relevant from the chapter map, timeline labels, and reading events, "
                "and what can potentially be skipped or deprioritized. "
                "If the syllabus does not explicitly list chapters, say that clearly and infer focus areas only from reading labels, exams, assignments, and timing. "
                "Ask targeted follow-up questions when needed, especially about which chapters or topics the student can skip, "
                "what they already know, and whether their exam schedule is fixed or flexible. "
                "When recommending access strategy, compare the available options already present in the rental recommendations: "
                "short-term rental windows, borrowable/open-access options, previews, used textbook purchase, and new purchase. "
                "Prefer the lowest-cost option that still covers the needed study period and format preference. "
                "Respond in concise markdown with these sections when useful: "
                "Current Profile, Knowledge Map, Likely Needed Duration, What May Be Skippable, Best Access Strategy, Next Question. "
                "Do not fabricate provider data or chapter numbers."
            ),
        },
        {
            "role": "user",
            "content": (
                "Student context:\n"
                f"- Known topics: {user_context.known_topics or 'Not provided'}\n"
                f"- Budget: {user_context.budget or 'Not provided'}\n"
                f"- Preferred textbook format: {user_context.textbook_format_preference or 'Not provided'}\n"
                f"- Exam dates flexibility: {user_context.exam_date_flexibility or 'Not provided'}\n\n"
                f"Syllabus analysis JSON:\n{json.dumps(compact_analysis, indent=2)}\n\n"
                f"Recent chat history:\n{chr(10).join(history_lines) if history_lines else 'None'}\n\n"
                f"Latest student message:\n{user_message}"
            ),
        },
    ]


def call_openai_for_study_planner(
    analysis: Dict[str, Any],
    user_context: StudyPlannerUserContext,
    user_message: str,
    chat_history: List[ChatMessage],
) -> Dict[str, Any]:
    response = client.responses.create(
        model="gpt-4o",
        input=build_study_planner_prompt(
            analysis=analysis,
            user_context=user_context,
            user_message=user_message,
            chat_history=chat_history,
        ),
    )

    answer = response.output_text.strip()
    if not answer:
        raise ValueError("Study planner did not return a response.")

    return {"assistant_message": answer}


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


@app.get("/")
def root() -> Dict[str, str]:
    return {
        "message": "PDF to JSON API is running. Use POST /parse-pdf or /analyze-syllabus"
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


@app.post("/analyze-syllabus", response_model=Dict[str, Any])
async def analyze_syllabus(
    file: UploadFile = File(...)
) -> Dict[str, Any]:
    """
    Upload a PDF syllabus, extract books and schedule information,
    and return rental timing recommendations per book.
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

        result = call_openai_for_syllabus_analysis(
            pdf_text=extracted_text,
        )

        if not isinstance(result, dict):
            raise HTTPException(status_code=500, detail="AI did not return a valid syllabus analysis object")

        result["rental_recommendations"] = await enrich_recommendations_with_provider_pricing(
            result.get("rental_recommendations", [])
        )

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


@app.post("/chat-study-plan", response_model=Dict[str, Any])
async def chat_study_plan(payload: StudyPlannerRequest) -> Dict[str, Any]:
    """
    Generate a personalized study and textbook access strategy from syllabus analysis and user context.
    """
    if not payload.analysis.get("books"):
        raise HTTPException(status_code=400, detail="Analysis payload must include at least one detected book.")

    try:
        return call_openai_for_study_planner(
            analysis=payload.analysis,
            user_context=payload.user_context,
            user_message=payload.user_message,
            chat_history=payload.chat_history,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
