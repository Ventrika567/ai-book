from typing import Any, Dict, List

import httpx

from config import EDS_PROFILE, EDS_API_TOKEN, EDS_BASE_URL


async def search_raw(
    book_title: str, author: str = "", isbn: str = "",
) -> List[Dict[str, Any]]:
    """Query EBSCO Discovery Service."""
    if not EDS_PROFILE or not EDS_API_TOKEN:
        return []

    headers = {
        "x-sessionToken": EDS_API_TOKEN,
        "Accept": "application/json",
    }
    params = {"query": book_title, "profile": EDS_PROFILE, "resultsperpage": 10}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(EDS_BASE_URL, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    return data.get("SearchResult", {}).get("Data", {}).get("Records", [])


def normalize_for_llm(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    items = raw_result.get("Items", [])
    title = next((item.get("Data") for item in items if item.get("Name") == "Title"), "")
    author_value = next((item.get("Data") for item in items if item.get("Name") in {"Author", "Authors"}), "")
    authors = author_value if isinstance(author_value, list) else ([author_value] if author_value else [])
    return {
        "title": title,
        "authors": authors,
    }


def extract_provider_id(matched_result: Dict[str, Any]) -> str:
    header = matched_result.get("Header", {})
    return f"{header.get('DbId', '')}:{header.get('An', '')}"


def build_provider_link(matched_result: Dict[str, Any]) -> str:
    # EDS doesn't consistently provide direct links
    return ""


async def get_detail(matched_result: Dict[str, Any]) -> Dict[str, Any]:
    """EDS entries are discovery results (typically library borrow)."""
    items = matched_result.get("Items", [])
    title = next((item.get("Data") for item in items if item.get("Name") == "Title"), "")
    return {
        "provider": "eds",
        "provider_link": build_provider_link(matched_result),
        "provider_book_id": extract_provider_id(matched_result),
        "book_info": {
            "title": title,
        },
        "estimated_cost": 0.0,
        "acquisition_mode": "borrow",
    }
