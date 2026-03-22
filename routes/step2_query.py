import asyncio
import json
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from llm import call_llm_structured
from models import BOOK_MATCH_SCHEMA
from providers import PROVIDERS, search_all_providers

router = APIRouter()


class QueryProvidersRequest(BaseModel):
    books: List[Dict[str, Any]]


MATCH_SYSTEM_PROMPT = """You are a highly helpful book matching assistant. Given a reference book (the book a student needs) and a list of search results from a book provider API, pick the best matching result.

Consider: title similarity, author match, edition match, ISBN match, year match.

### LENIENCY RULE:
Even if the match isn't perfect, pick the result that is MOST LIKELY to be the correct book or a newer/older edition of it. Only return -1 if the results are completely irrelevant (e.g., a cookbook when searching for a physics text).

Return JSON with:
- best_match_index: integer index into the results array, or -1 if absolutely no relation
- confidence: float 0-1
- reason: brief explanation of why this was picked as the closest match"""


async def _match_book_to_provider(
    book: Dict[str, Any],
    provider_name: str,
    raw_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Use LLM to pick the best match from a provider's search results."""
    provider_module = PROVIDERS[provider_name]

    # Normalize results for LLM (reduce tokens)
    normalized = [provider_module.normalize_for_llm(r) for r in raw_results]

    user_prompt = (
        f"Reference book: {json.dumps(book, ensure_ascii=False)}\n\n"
        f"Provider: {provider_name}\n"
        f"Search results ({len(normalized)} candidates):\n"
        f"{json.dumps(normalized, indent=2, ensure_ascii=False)}\n\n"
        "Pick the best matching result."
    )

    try:
        match_result = await call_llm_structured(
            system_prompt=MATCH_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema=BOOK_MATCH_SCHEMA,
            schema_name="book_match",
        )

        best_idx = match_result.get("best_match_index", -1)
        
        # Fallback: If LLM failed to pick or picked -1 but we have results, 
        # let's be lenient and pick the first one if it looks remotely similar
        if (best_idx < 0 or best_idx >= len(raw_results)) and raw_results:
            best_idx = 0

        if best_idx < 0:
            return None

        matched_raw = raw_results[best_idx]

        # Get full detail from provider
        detail = await provider_module.get_detail(matched_raw)
        detail["match_confidence"] = match_result.get("confidence", 0.5) if best_idx == 0 and match_result.get("best_match_index") == -1 else match_result.get("confidence", 0)
        detail["match_reason"] = match_result.get("reason", "Lenient fallback match.") if best_idx == 0 and match_result.get("best_match_index") == -1 else match_result.get("reason", "")
        return detail

    except Exception:
        # Final fallback: just return the first one
        if raw_results:
            return await provider_module.get_detail(raw_results[0])
        return None


async def _query_all_providers_for_book(
    book: Dict[str, Any],
) -> Dict[str, Any]:
    """Search all providers for a single book and LLM-match results."""
    book_title = book.get("bookname", "")
    author = book.get("author", "")
    isbn = book.get("isbn", "")

    # Fan out to all providers
    all_raw_results = await search_all_providers(book_title, author=author, isbn=isbn)

    # LLM-match each provider's results in parallel
    match_tasks = []
    provider_names = []
    for provider_name, raw_results in all_raw_results.items():
        if raw_results:
            match_tasks.append(
                _match_book_to_provider(book, provider_name, raw_results)
            )
            provider_names.append(provider_name)

    match_results = await asyncio.gather(*match_tasks, return_exceptions=True)

    providers = []
    for provider_name, result in zip(provider_names, match_results):
        if isinstance(result, Exception) or result is None:
            continue
        providers.append(result)

    return {
        "bookname": book_title,
        "providers": providers,
    }


@router.post("/query-providers")
async def query_providers(request: QueryProvidersRequest) -> List[Dict[str, Any]]:
    """For each book, query all providers and LLM-match results."""
    if not request.books:
        raise HTTPException(status_code=400, detail="No books provided.")

    # Process all books in parallel
    tasks = [_query_all_providers_for_book(book) for book in request.books]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    output = []
    for result in results:
        if isinstance(result, Exception):
            continue
        output.append(result)

    return output
