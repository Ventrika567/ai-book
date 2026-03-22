from typing import Any, Dict, List

import httpx

from config import GOOGLE_BOOKS_VOLUMES_URL, GOOGLE_BOOKS_API_KEY


async def search_raw(
    book_title: str, author: str = "", isbn: str = "",
) -> List[Dict[str, Any]]:
    """Query Google Books API, return raw candidate list."""
    query_parts = [f'intitle:"{book_title}"']
    if author:
        query_parts.append(f'inauthor:"{author}"')
    if isbn:
        query_parts.append(f"isbn:{isbn}")

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

    return data.get("items", [])


def normalize_for_llm(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract essential fields for LLM matching."""
    volume_info = raw_result.get("volumeInfo", {})
    industry_ids = volume_info.get("industryIdentifiers", [])
    isbns = [entry.get("identifier") for entry in industry_ids if entry.get("identifier")]
    return {
        "title": volume_info.get("title", ""),
        "authors": volume_info.get("authors", []),
        "isbn": isbns[0] if isbns else "",
        "year": volume_info.get("publishedDate", ""),
    }


def extract_provider_id(matched_result: Dict[str, Any]) -> str:
    """Extract Google Books volume ID."""
    return matched_result.get("id") or ""


def build_provider_link(matched_result: Dict[str, Any]) -> str:
    """Construct the user-facing URL."""
    volume_info = matched_result.get("volumeInfo", {})
    sale_info = matched_result.get("saleInfo", {})
    return (
        sale_info.get("buyLink")
        or volume_info.get("infoLink")
        or volume_info.get("previewLink")
        or ""
    )


async def get_detail(matched_result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract pricing from the already-fetched volume data."""
    volume_info = matched_result.get("volumeInfo", {})
    sale_info = matched_result.get("saleInfo", {})
    access_info = matched_result.get("accessInfo", {})
    industry_ids = volume_info.get("industryIdentifiers", [])
    isbns = [entry.get("identifier") for entry in industry_ids if entry.get("identifier")]

    detail: Dict[str, Any] = {
        "provider": "google_books",
        "provider_link": build_provider_link(matched_result),
        "provider_book_id": extract_provider_id(matched_result),
        "book_info": {
            "title": volume_info.get("title", ""),
            "authors": volume_info.get("authors", []),
            "isbn": isbns[0] if isbns else "",
            "year": volume_info.get("publishedDate", ""),
        },
    }

    list_price = sale_info.get("listPrice", {}).get("amount")
    buy_link = sale_info.get("buyLink")

    if isinstance(list_price, (int, float)) and buy_link:
        detail["estimated_cost"] = float(list_price)
        detail["acquisition_mode"] = "buy"
        detail["price_type"] = "google_books"
        detail["provider_link"] = buy_link
    elif access_info.get("viewability") in {"ALL_PAGES", "PARTIAL"}:
        preview_link = volume_info.get("previewLink") or volume_info.get("infoLink")
        detail["estimated_cost"] = 0.0
        detail["acquisition_mode"] = "borrow"
        if preview_link:
            detail["provider_link"] = preview_link
    else:
        detail["estimated_cost"] = None
        detail["acquisition_mode"] = ""

    return detail
