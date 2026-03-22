from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class FinalizeRequest(BaseModel):
    extraction: Dict[str, Any]  # Original SyllabusExtraction
    best_selections: List[Dict[str, Any]]  # Output from step3


@router.post("/finalize-results")
async def finalize_results(request: FinalizeRequest) -> List[Dict[str, Any]]:
    """Join best provider selections with original extraction data (dates, schedule)."""
    books = request.extraction.get("books", [])
    schedule_items = request.extraction.get("schedule_items", [])
    selections = request.best_selections

    # Build a lookup from bookname -> selection
    selection_map: Dict[str, Dict[str, Any]] = {}
    for sel in selections:
        bookname = sel.get("bookname", "")
        if bookname:
            selection_map[bookname] = sel

    results: List[Dict[str, Any]] = []
    for book in books:
        bookname = book.get("bookname", "")
        selection = selection_map.get(bookname, {})
        best_provider = selection.get("best_provider")

        # Find schedule items related to this book (simple keyword match in labels)
        book_schedule = []
        bookname_lower = bookname.lower()
        for item in schedule_items:
            label_lower = (item.get("label") or "").lower()
            date_text_lower = (item.get("date_text") or "").lower()
            # Include if bookname words appear in label/date_text, or if it's a general item
            if any(word in label_lower or word in date_text_lower for word in bookname_lower.split() if len(word) > 3):
                book_schedule.append(item)

        # If only 1 book, all schedule items are relevant
        if len(books) == 1:
            book_schedule = schedule_items

        result: Dict[str, Any] = {
            "bookname": bookname,
            "author": book.get("author", ""),
            "edition": book.get("edition", ""),
            "year": book.get("year", ""),
            "isbn": book.get("isbn", ""),
            "date_periods": book.get("date_periods", []),
            "best_provider": best_provider,
            "provider_link": best_provider.get("provider_link", "") if best_provider else "",
            "selection_reason": selection.get("reason", ""),
            "schedule_items": book_schedule,
        }
        results.append(result)

    return results
