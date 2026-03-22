import asyncio
from typing import Any, Dict, List

from providers import (
    openlibrary,
    google_books,
    ecampus,
    internet_archive,
    hathitrust,
    worldcat,
    doab,
    oapen,
    primo,
    eds,
)

PROVIDERS = {
    "openlibrary": openlibrary,
    "google_books": google_books,
    "ecampus": ecampus,
    "internet_archive": internet_archive,
    "hathitrust": hathitrust,
    "worldcat": worldcat,
    "doab": doab,
    "oapen": oapen,
    "primo": primo,
    "eds": eds,
}


async def search_all_providers(
    book_title: str,
    author: str = "",
    isbn: str = "",
) -> Dict[str, List[Dict[str, Any]]]:
    """Fan out search to all providers in parallel. Returns {provider_name: raw_results}."""
    names = list(PROVIDERS.keys())
    tasks = [
        PROVIDERS[name].search_raw(book_title, author=author, isbn=isbn)
        for name in names
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    output: Dict[str, List[Dict[str, Any]]] = {}
    for name, result in zip(names, results):
        if isinstance(result, Exception) or not result:
            continue
        output[name] = result
    return output
