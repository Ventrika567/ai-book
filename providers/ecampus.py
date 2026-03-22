from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

import httpx

from config import (
    ECAMPUS_URL,
    ECAMPUS_SOAP_ACTION,
    OPEN_LIBRARY_SEARCH_URL,
)


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

    if ebook_price_elem is None and used_price_elem is None and new_price_elem is None:
        raise ValueError("Missing price fields in response")

    return {
        "new_price": parse_optional_float(new_price_elem),
        "used_price": parse_optional_float(used_price_elem),
        "ebook_price": parse_optional_float(ebook_price_elem),
        "new_url": new_url_elem.text.strip() if new_url_elem is not None and new_url_elem.text else None,
        "used_url": used_url_elem.text.strip() if used_url_elem is not None and used_url_elem.text else None,
        "ebook_url": ebook_url_elem.text.strip() if ebook_url_elem is not None and ebook_url_elem.text else None,
    }


async def _get_isbn_from_title(title: str, author: str = "") -> Optional[str]:
    """Resolve a book title to an ISBN via Open Library."""
    params: Dict[str, Any] = {
        "title": title,
        "limit": 3,
        "fields": "key,title,author_name,isbn",
    }
    if author:
        params["author"] = author

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
    """eCampus doesn't have a title search API.
    We resolve ISBN via Open Library, then return a single-item list with the ISBN."""
    resolved_isbn = isbn or await _get_isbn_from_title(book_title, author)
    if not resolved_isbn:
        return []

    return [{"isbn": resolved_isbn, "title": book_title, "source": "isbn_resolve"}]


def normalize_for_llm(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract essential fields for LLM matching."""
    return {
        "title": raw_result.get("title", ""),
        "isbn": raw_result.get("isbn", ""),
    }


def extract_provider_id(matched_result: Dict[str, Any]) -> str:
    """eCampus uses ISBN as its ID."""
    return matched_result.get("isbn") or ""


def build_provider_link(pricing: Dict[str, Any]) -> str:
    """Get best buy URL from pricing data."""
    for key in ["used_url", "ebook_url", "new_url"]:
        url = pricing.get(key)
        if url:
            return url
    return ""


async def get_detail(matched_result: Dict[str, Any]) -> Dict[str, Any]:
    """Call eCampus SOAP API for pricing."""
    isbn = matched_result.get("isbn") or ""
    detail: Dict[str, Any] = {
        "provider": "ecampus",
        "provider_book_id": isbn,
        "book_info": {"isbn": isbn, "title": matched_result.get("title", "")},
    }

    if not isbn:
        detail["estimated_cost"] = None
        detail["acquisition_mode"] = ""
        detail["provider_link"] = ""
        return detail

    try:
        payload = build_soap_payload(isbn)
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": ECAMPUS_SOAP_ACTION,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(ECAMPUS_URL, content=payload, headers=headers)
            resp.raise_for_status()
            pricing = parse_ecampus_response(resp.content)

        # Find lowest price
        prices = {
            "ebook": pricing.get("ebook_price"),
            "used": pricing.get("used_price"),
            "new": pricing.get("new_price"),
        }
        valid_prices = {k: v for k, v in prices.items() if isinstance(v, (int, float)) and v >= 0}

        if valid_prices:
            best_type = min(valid_prices, key=valid_prices.get)
            detail["estimated_cost"] = valid_prices[best_type]
            detail["price_type"] = best_type
            detail["acquisition_mode"] = "buy"
            detail["provider_link"] = build_provider_link(pricing)
            detail["book_info"]["pricing"] = pricing
        else:
            detail["estimated_cost"] = None
            detail["acquisition_mode"] = ""
            detail["provider_link"] = ""
    except Exception:
        detail["estimated_cost"] = None
        detail["acquisition_mode"] = ""
        detail["provider_link"] = ""

    return detail
