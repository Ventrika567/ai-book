import asyncio
import json
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from llm import call_llm_structured
from models import BEST_PROVIDER_SCHEMA

router = APIRouter()


class BookProviderEntry(BaseModel):
    bookname: str
    providers: List[Dict[str, Any]]


class SelectBestProviderRequest(BaseModel):
    book_results: List[BookProviderEntry]


SELECT_SYSTEM_PROMPT = """You are a textbook cost optimizer. Given a list of provider options for a textbook, each with different pricing, availability, and access modes, select the single best option for a student who wants the lowest cost.

Rules:
- Free/borrow options (cost $0 or null with acquisition_mode "borrow") with working links are always preferred over paid options
- Among paid options, pick the cheapest
- If two options have the same cost, prefer the one with a provider_link
- If no options have pricing data, pick the one with the best access link

Return JSON with:
- best_provider_index: integer index into the providers array
- reason: brief explanation of why this is the best option"""


async def _select_best_for_book(entry: BookProviderEntry) -> Dict[str, Any]:
    """Use LLM to select the best provider for a single book."""
    if not entry.providers:
        # Fallback for when absolutely no provider matched
        fallback_title = entry.bookname.replace(" ", "+")
        return {
            "bookname": entry.bookname,
            "best_provider": {
                "provider": "Global Search",
                "estimated_cost": 0.0,
                "acquisition_mode": "purchase/rent",
                "price_type": "Market Price",
                "provider_link": f"https://www.google.com/search?q={fallback_title}+textbook+rental",
                "book_info": {"title": entry.bookname}
            },
            "reason": "No direct matches found. Provided a global search fallback to ensure you can still find the material.",
        }

    if len(entry.providers) == 1:
        return {
            "bookname": entry.bookname,
            "best_provider": entry.providers[0],
            "reason": "Only one provider available.",
        }

    # Prepare a summary for the LLM
    provider_summaries = []
    for i, p in enumerate(entry.providers):
        summary = {
            "index": i,
            "provider": p.get("provider", ""),
            "estimated_cost": p.get("estimated_cost"),
            "acquisition_mode": p.get("acquisition_mode", ""),
            "price_type": p.get("price_type", ""),
            "provider_link": p.get("provider_link", ""),
            "title": p.get("book_info", {}).get("title", ""),
        }
        provider_summaries.append(summary)

    user_prompt = (
        f"Book: {entry.bookname}\n\n"
        f"Available providers ({len(provider_summaries)} options):\n"
        f"{json.dumps(provider_summaries, indent=2, ensure_ascii=False)}\n\n"
        "Select the best provider."
    )

    try:
        selection = await call_llm_structured(
            system_prompt=SELECT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema=BEST_PROVIDER_SCHEMA,
            schema_name="best_provider_selection",
        )

        best_idx = selection.get("best_provider_index", 0)
        if best_idx < 0 or best_idx >= len(entry.providers):
            best_idx = 0

        return {
            "bookname": entry.bookname,
            "best_provider": entry.providers[best_idx],
            "reason": selection.get("reason", ""),
        }
    except Exception:
        # Fallback: pick the first provider with lowest cost
        sorted_providers = sorted(
            entry.providers,
            key=lambda p: (
                0 if p.get("acquisition_mode") == "borrow" else 1,
                p.get("estimated_cost") if isinstance(p.get("estimated_cost"), (int, float)) else float("inf"),
            ),
        )
        return {
            "bookname": entry.bookname,
            "best_provider": sorted_providers[0],
            "reason": "Fallback: selected cheapest option.",
        }


@router.post("/select-best-provider")
async def select_best_provider(request: SelectBestProviderRequest) -> List[Dict[str, Any]]:
    """For each book, select the best provider from the query results."""
    if not request.book_results:
        raise HTTPException(status_code=400, detail="No book results provided.")

    tasks = [_select_best_for_book(entry) for entry in request.book_results]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    output = []
    for result in results:
        if isinstance(result, Exception):
            continue
        output.append(result)

    return output
