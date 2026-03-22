from typing import Any, Dict, List

import httpx

from config import INTERNET_ARCHIVE_ADVANCED_SEARCH_URL


async def search_raw(
    book_title: str, author: str = "", isbn: str = "",
) -> List[Dict[str, Any]]:
    """Query Internet Archive advanced search, return raw candidate list."""
    query = f'title:("{book_title}") AND mediatype:texts'
    if author:
        query += f' AND creator:("{author}")'

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

    return data.get("response", {}).get("docs", [])


def normalize_for_llm(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract essential fields for LLM matching."""
    creator = raw_result.get("creator")
    creators = creator if isinstance(creator, list) else ([creator] if creator else [])
    return {
        "title": raw_result.get("title", ""),
        "authors": creators,
        "year": raw_result.get("year"),
    }


def extract_provider_id(matched_result: Dict[str, Any]) -> str:
    """Extract Internet Archive identifier."""
    return matched_result.get("identifier") or ""


def build_provider_link(matched_result: Dict[str, Any]) -> str:
    """Construct the user-facing URL."""
    identifier = matched_result.get("identifier")
    return f"https://archive.org/details/{identifier}" if identifier else ""


async def get_detail(matched_result: Dict[str, Any]) -> Dict[str, Any]:
    """Internet Archive items are free to borrow."""
    creator = matched_result.get("creator")
    creators = creator if isinstance(creator, list) else ([creator] if creator else [])
    return {
        "provider": "internet_archive",
        "provider_link": build_provider_link(matched_result),
        "provider_book_id": extract_provider_id(matched_result),
        "book_info": {
            "title": matched_result.get("title", ""),
            "authors": creators,
            "year": matched_result.get("year"),
        },
        "estimated_cost": 0.0,
        "acquisition_mode": "borrow",
    }
