from typing import Any, Dict, List

import httpx

from config import DOAB_SEARCH_URL


async def search_raw(
    book_title: str, author: str = "", isbn: str = "",
) -> List[Dict[str, Any]]:
    """Query DOAB (Directory of Open Access Books)."""
    params = {"lookfor": book_title, "type": "AllFields", "limit": 10}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(DOAB_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    return data.get("records", []) if isinstance(data, dict) else []


def normalize_for_llm(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    authors = raw_result.get("authors", [])
    if isinstance(authors, str):
        authors = [authors]
    return {
        "title": raw_result.get("title", ""),
        "authors": authors,
    }


def extract_provider_id(matched_result: Dict[str, Any]) -> str:
    return str(matched_result.get("id") or "")


def build_provider_link(matched_result: Dict[str, Any]) -> str:
    return matched_result.get("url") or ""


async def get_detail(matched_result: Dict[str, Any]) -> Dict[str, Any]:
    """DOAB entries are open access (free)."""
    authors = matched_result.get("authors", [])
    if isinstance(authors, str):
        authors = [authors]
    return {
        "provider": "doab",
        "provider_link": build_provider_link(matched_result),
        "provider_book_id": extract_provider_id(matched_result),
        "book_info": {
            "title": matched_result.get("title", ""),
            "authors": authors,
        },
        "estimated_cost": 0.0,
        "acquisition_mode": "borrow",
    }
