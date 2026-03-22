from typing import Any, Dict, List, Optional

import httpx

from config import OPEN_LIBRARY_SEARCH_URL, OPEN_LIBRARY_WORK_URL, OPEN_LIBRARY_BOOK_URL


async def search_raw(
    book_title: str, author: str = "", isbn: str = "",
) -> List[Dict[str, Any]]:
    """Query Open Library search API, return raw candidate list."""
    params: Dict[str, Any] = {
        "title": book_title,
        "limit": 10,
        "fields": "key,title,author_name,first_publish_year,isbn",
    }
    if author:
        params["author"] = author
    if isbn:
        params["isbn"] = isbn

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(OPEN_LIBRARY_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    return data.get("docs", [])


def normalize_for_llm(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract essential fields for LLM matching."""
    isbns = raw_result.get("isbn") or []
    return {
        "title": raw_result.get("title", ""),
        "authors": raw_result.get("author_name") or [],
        "isbn": isbns[0] if isbns else "",
        "year": raw_result.get("first_publish_year"),
    }


def extract_provider_id(matched_result: Dict[str, Any]) -> str:
    """Extract Open Library work key."""
    return matched_result.get("key") or ""


def build_provider_link(matched_result: Dict[str, Any]) -> str:
    """Construct the user-facing URL."""
    work_key = matched_result.get("key")
    isbns = matched_result.get("isbn") or []
    if work_key:
        return f"{OPEN_LIBRARY_WORK_URL}{work_key}"
    if isbns:
        return f"{OPEN_LIBRARY_BOOK_URL}/{isbns[0]}"
    return OPEN_LIBRARY_SEARCH_URL


async def get_detail(matched_result: Dict[str, Any]) -> Dict[str, Any]:
    """Get availability info using ISBN lookup."""
    isbns = matched_result.get("isbn") or []
    primary_isbn = isbns[0] if isbns else None

    detail: Dict[str, Any] = {
        "provider": "openlibrary",
        "provider_link": build_provider_link(matched_result),
        "provider_book_id": extract_provider_id(matched_result),
        "book_info": {
            "title": matched_result.get("title", ""),
            "authors": matched_result.get("author_name") or [],
            "isbn": primary_isbn,
            "year": matched_result.get("first_publish_year"),
        },
    }

    if not primary_isbn:
        detail["estimated_cost"] = None
        detail["acquisition_mode"] = "borrow"
        return detail

    # Check availability via search API
    try:
        params = {
            "q": f"isbn:{primary_isbn}",
            "limit": 1,
            "fields": "title,author_name,availability",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(OPEN_LIBRARY_SEARCH_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        docs = data.get("docs", [])
        if docs:
            availability = docs[0].get("availability") or {}
            if availability.get("is_readable") or availability.get("is_lendable") or availability.get("status") == "open":
                detail["estimated_cost"] = 0.0
            else:
                detail["estimated_cost"] = None
        else:
            detail["estimated_cost"] = None
    except Exception:
        detail["estimated_cost"] = None

    detail["acquisition_mode"] = "borrow"
    return detail
