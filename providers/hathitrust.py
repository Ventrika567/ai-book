from typing import Any, Dict, List, Optional

import httpx

from config import HATHITRUST_ISBN_API_URL, OPEN_LIBRARY_SEARCH_URL


async def _get_isbn_from_title(title: str) -> Optional[str]:
    """Resolve a book title to an ISBN via Open Library."""
    params = {"title": title, "limit": 3, "fields": "isbn"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(OPEN_LIBRARY_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    for doc in data.get("docs", []):
        isbns = doc.get("isbn") or []
        if isbns:
            return isbns[0]
    return None


async def search_raw(
    book_title: str, author: str = "", isbn: str = "",
) -> List[Dict[str, Any]]:
    """HathiTrust requires ISBN for lookup. Resolve from title if needed."""
    resolved_isbn = isbn or await _get_isbn_from_title(book_title)
    if not resolved_isbn:
        return []

    endpoint = f"{HATHITRUST_ISBN_API_URL}/{resolved_isbn}.json"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(endpoint)
        resp.raise_for_status()
        data = resp.json()

    records = data.get("records", {})
    if not records:
        return []

    # Return all records as candidates
    results = []
    for record_id, record in records.items():
        record["_isbn_used"] = resolved_isbn
        record["_record_id"] = record_id
        results.append(record)
    return results


def normalize_for_llm(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract essential fields for LLM matching."""
    titles = raw_result.get("titles", [])
    title = titles[0].get("title", "") if titles else ""
    authors = [a.get("name") for a in raw_result.get("authors", []) if a.get("name")]
    return {
        "title": title,
        "authors": authors,
        "isbn": raw_result.get("_isbn_used", ""),
    }


def extract_provider_id(matched_result: Dict[str, Any]) -> str:
    """Extract HathiTrust record URL."""
    return matched_result.get("recordURL") or ""


def build_provider_link(matched_result: Dict[str, Any]) -> str:
    return matched_result.get("recordURL") or ""


async def get_detail(matched_result: Dict[str, Any]) -> Dict[str, Any]:
    """HathiTrust items are free to borrow."""
    titles = matched_result.get("titles", [])
    title = titles[0].get("title", "") if titles else ""
    authors = [a.get("name") for a in matched_result.get("authors", []) if a.get("name")]
    return {
        "provider": "hathitrust",
        "provider_link": build_provider_link(matched_result),
        "provider_book_id": extract_provider_id(matched_result),
        "book_info": {
            "title": title,
            "authors": authors,
            "isbn": matched_result.get("_isbn_used", ""),
        },
        "estimated_cost": 0.0,
        "acquisition_mode": "borrow",
    }
