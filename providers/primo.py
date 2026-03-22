from typing import Any, Dict, List

import httpx

from config import PRIMO_API_KEY, PRIMO_BASE_URL, PRIMO_VIEW


async def search_raw(
    book_title: str, author: str = "", isbn: str = "",
) -> List[Dict[str, Any]]:
    """Query Primo library discovery platform."""
    if not PRIMO_API_KEY or not PRIMO_BASE_URL or not PRIMO_VIEW:
        return []

    params = {
        "vid": PRIMO_VIEW,
        "q": f"any,contains,{book_title}",
        "limit": 10,
        "apikey": PRIMO_API_KEY,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{PRIMO_BASE_URL.rstrip('/')}/primo/v1/search", params=params)
        resp.raise_for_status()
        data = resp.json()

    return data.get("docs", [])


def normalize_for_llm(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    pnx = raw_result.get("pnx", {})
    display = pnx.get("display", {})
    title_field = display.get("title")
    title = title_field[0] if isinstance(title_field, list) else (title_field or "")
    creators = display.get("creator", [])
    if isinstance(creators, str):
        creators = [creators]
    return {
        "title": title,
        "authors": creators,
    }


def extract_provider_id(matched_result: Dict[str, Any]) -> str:
    return matched_result.get("pnx", {}).get("control", {}).get("recordid") or ""


def build_provider_link(matched_result: Dict[str, Any]) -> str:
    pnx = matched_result.get("pnx", {})
    links = pnx.get("links", {})
    linktohtml = links.get("linktorsrc") or []
    return linktohtml[0] if linktohtml else ""


async def get_detail(matched_result: Dict[str, Any]) -> Dict[str, Any]:
    """Primo entries are library catalog entries (free)."""
    pnx = matched_result.get("pnx", {})
    display = pnx.get("display", {})
    title_field = display.get("title")
    title = title_field[0] if isinstance(title_field, list) else (title_field or "")
    creators = display.get("creator", [])
    if isinstance(creators, str):
        creators = [creators]
    return {
        "provider": "primo",
        "provider_link": build_provider_link(matched_result),
        "provider_book_id": extract_provider_id(matched_result),
        "book_info": {
            "title": title,
            "authors": creators,
        },
        "estimated_cost": 0.0,
        "acquisition_mode": "borrow",
    }
