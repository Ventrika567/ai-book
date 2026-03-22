from typing import Any, Dict, List

import httpx

from config import OAPEN_SEARCH_URL


async def search_raw(
    book_title: str, author: str = "", isbn: str = "",
) -> List[Dict[str, Any]]:
    """Query OAPEN (Open Access Publishing in European Networks)."""
    params = {"query": book_title, "size": 10}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(OAPEN_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    return data.get("results", []) if isinstance(data, dict) else []


def normalize_for_llm(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    creators = raw_result.get("creators", [])
    if isinstance(creators, str):
        creators = [creators]
    return {
        "title": raw_result.get("title", ""),
        "authors": creators,
    }


def extract_provider_id(matched_result: Dict[str, Any]) -> str:
    return str(matched_result.get("id") or "")


def build_provider_link(matched_result: Dict[str, Any]) -> str:
    return matched_result.get("url") or ""


async def get_detail(matched_result: Dict[str, Any]) -> Dict[str, Any]:
    """OAPEN entries are open access (free)."""
    creators = matched_result.get("creators", [])
    if isinstance(creators, str):
        creators = [creators]
    return {
        "provider": "oapen",
        "provider_link": build_provider_link(matched_result),
        "provider_book_id": extract_provider_id(matched_result),
        "book_info": {
            "title": matched_result.get("title", ""),
            "authors": creators,
        },
        "estimated_cost": 0.0,
        "acquisition_mode": "borrow",
    }
