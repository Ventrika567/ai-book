from typing import Any, Dict, List

import httpx

from config import WORLDCAT_SEARCH_V2_URL, WORLDCAT_API_KEY


async def search_raw(
    book_title: str, author: str = "", isbn: str = "",
) -> List[Dict[str, Any]]:
    """Query WorldCat Search API v2."""
    if not WORLDCAT_API_KEY:
        return []

    headers = {"Authorization": f"Bearer {WORLDCAT_API_KEY}", "Accept": "application/json"}
    query_parts = [f'ti:"{book_title}"']
    if author:
        query_parts.append(f'au:"{author}"')
    if isbn:
        query_parts.append(f"isbn:{isbn}")

    params = {"q": " AND ".join(query_parts), "limit": 10}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(WORLDCAT_SEARCH_V2_URL, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    return data.get("briefRecords", [])


def normalize_for_llm(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": raw_result.get("title", ""),
        "authors": [raw_result.get("creator")] if raw_result.get("creator") else [],
        "isbn": (raw_result.get("isbns") or [""])[0],
        "edition": raw_result.get("edition", ""),
    }


def extract_provider_id(matched_result: Dict[str, Any]) -> str:
    return str(matched_result.get("oclcNumber") or "")


def build_provider_link(matched_result: Dict[str, Any]) -> str:
    return matched_result.get("catalogUrl") or ""


async def get_detail(matched_result: Dict[str, Any]) -> Dict[str, Any]:
    """WorldCat entries are library catalog links (free)."""
    return {
        "provider": "worldcat",
        "provider_link": build_provider_link(matched_result),
        "provider_book_id": extract_provider_id(matched_result),
        "book_info": {
            "title": matched_result.get("title", ""),
            "authors": [matched_result.get("creator")] if matched_result.get("creator") else [],
            "isbns": matched_result.get("isbns") or [],
        },
        "estimated_cost": 0.0,
        "acquisition_mode": "borrow",
    }
