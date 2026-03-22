import asyncio
import os
import unittest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import (  # noqa: E402
    build_edition_warning,
    build_book_timelines,
    build_rental_recommendations,
    build_book_lookup_request,
    extract_first_isbn,
    is_actionable_provider_option,
    is_reasonable_provider_match,
    merge_rental_windows,
    resolve_schedule_dates,
    resolve_book_reference,
    score_provider_candidate,
    select_best_provider_candidate,
    sort_provider_options,
    summarize_acquisition_decision,
    try_parse_date,
)


class SyllabusAnalysisTests(unittest.TestCase):
    def test_try_parse_date_with_explicit_year(self) -> None:
        self.assertEqual(str(try_parse_date("September 5, 2026")), "2026-09-05")

    def test_try_parse_date_with_fallback_year(self) -> None:
        self.assertEqual(str(try_parse_date("September 5", 2026)), "2026-09-05")

    def test_resolve_schedule_dates_from_week_label(self) -> None:
        resolved = resolve_schedule_dates(
            [
                {
                    "item_type": "reading",
                    "label": "Week 3 reading",
                    "raw_date_text": "Week 3",
                    "start_date": "",
                    "end_date": "",
                    "week_label": "Week 3",
                    "source_snippet": "Week 3 reading from textbook",
                    "confidence": 0.8,
                    "is_estimated": False,
                    "book_hint": {
                        "title_hint": "",
                        "author_hint": "",
                    },
                }
            ],
            {
                "course_start_date": "2026-01-12",
                "course_end_date": "",
                "term_label": "Spring 2026",
                "date_anchor_notes": [],
            },
        )

        item = resolved["schedule_items"][0]
        self.assertEqual(item["start_date"], "2026-01-26")
        self.assertTrue(item["is_estimated"])

    def test_build_book_timelines_matches_specific_book(self) -> None:
        books = [
            {"bookname": "Calculus", "author": "Stewart", "edition": "8th", "year": "2015"},
            {"bookname": "Physics", "author": "Halliday", "edition": "10th", "year": "2014"},
        ]
        schedule_items = [
            {
                "item_type": "reading",
                "label": "Read Stewart Calculus Chapter 2",
                "raw_date_text": "September 8, 2026",
                "start_date": "2026-09-08",
                "end_date": "2026-09-08",
                "week_label": "",
                "source_snippet": "Stewart Calculus chapter 2 due",
                "confidence": 0.9,
                "is_estimated": False,
                "book_hint": {
                    "title_hint": "Calculus",
                    "author_hint": "Stewart",
                },
            }
        ]

        timelines = build_book_timelines(books, schedule_items)
        calculus_timeline = next(item for item in timelines if item["book"]["bookname"] == "Calculus")
        physics_timeline = next(item for item in timelines if item["book"]["bookname"] == "Physics")

        self.assertEqual(len(calculus_timeline["matched_schedule_items"]), 1)
        self.assertEqual(len(physics_timeline["matched_schedule_items"]), 0)

    def test_merge_rental_windows_combines_nearby_ranges(self) -> None:
        merged = merge_rental_windows(
            [
                {
                    "start_date": "2026-09-01",
                    "end_date": "2026-09-08",
                    "is_estimated": False,
                    "triggering_items": [{"label": "Homework 1", "start_date": "2026-09-08", "end_date": "2026-09-08"}],
                },
                {
                    "start_date": "2026-09-10",
                    "end_date": "2026-09-14",
                    "is_estimated": False,
                    "triggering_items": [{"label": "Quiz 1", "start_date": "2026-09-12", "end_date": "2026-09-12"}],
                },
            ]
        )

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["start_date"], "2026-09-01")
        self.assertEqual(merged[0]["end_date"], "2026-09-14")

    def test_build_rental_recommendations_returns_periods(self) -> None:
        recommendations = build_rental_recommendations(
            [
                {
                    "book": {"bookname": "Calculus", "author": "Stewart", "edition": "8th", "year": "2015"},
                    "matched_schedule_items": [
                        {
                            "label": "Midterm Exam",
                            "item_type": "exam",
                            "start_date": "2026-10-10",
                            "end_date": "2026-10-10",
                            "is_estimated": False,
                            "matching_reason": "Matched",
                        }
                    ],
                }
            ]
        )

        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0]["book"]["bookname"], "Calculus")
        self.assertEqual(recommendations[0]["periods"][0]["start_date"], "2026-10-03")
        self.assertEqual(recommendations[0]["periods"][0]["end_date"], "2026-10-12")

    def test_summarize_acquisition_decision_prefers_borrow_when_free(self) -> None:
        summary = summarize_acquisition_decision(
            [
                {
                    "start_date": "2026-09-01",
                    "end_date": "2026-09-21",
                }
            ],
            {
                "provider_details": [],
                "best_provider": {
                    "provider": "openlibrary",
                    "acquisition_mode": "borrow",
                    "estimated_cost": 0.0,
                    "provider_link": "https://openlibrary.org",
                },
            },
        )

        self.assertEqual(summary["recommended_action"], "borrow")
        self.assertEqual(summary["recommended_duration_days"], 21)
        self.assertIn("openlibrary", summary["recommendation_reason"])

    def test_actionable_provider_requires_real_link(self) -> None:
        self.assertFalse(
            is_actionable_provider_option(
                {
                    "acquisition_mode": "buy",
                    "estimated_cost": 0.0,
                    "provider_link": None,
                }
            )
        )

    def test_summarize_acquisition_decision_falls_back_to_linked_option(self) -> None:
        summary = summarize_acquisition_decision(
            [
                {
                    "start_date": "2026-09-01",
                    "end_date": "2026-09-21",
                }
            ],
            {
                "provider_details": sort_provider_options(
                    [
                        {
                            "provider": "ecampus",
                            "acquisition_mode": "buy",
                            "estimated_cost": 0.0,
                            "provider_link": None,
                        },
                        {
                            "provider": "google_books",
                            "acquisition_mode": "borrow",
                            "estimated_cost": 0.0,
                            "provider_link": "https://books.google.com/example",
                        },
                    ]
                ),
                "best_provider": None,
            },
        )

        self.assertEqual(summary["best_provider"]["provider"], "google_books")
        self.assertEqual(summary["selected_link"], "https://books.google.com/example")
        self.assertTrue(
            is_actionable_provider_option(
                {
                    "acquisition_mode": "borrow",
                    "estimated_cost": 0.0,
                    "provider_link": "https://openlibrary.org/isbn/123",
                }
            )
        )

    def test_resolve_book_reference_prefers_syllabus_isbn(self) -> None:
        resolved = asyncio.run(
            resolve_book_reference(
                {
                    "bookname": "Big Java",
                    "author": "Horstmann",
                    "edition": "10th edition",
                    "year": "2020",
                    "isbn": "ISBN 978-1-119-49909-1",
                }
            )
        )

        self.assertEqual(resolved["isbn"], extract_first_isbn("978-1-119-49909-1"))
        self.assertEqual(resolved["match_source"], "syllabus_isbn")

    def test_build_edition_warning_detects_mismatch(self) -> None:
        warning = build_edition_warning(
            "10th edition",
            {
                "title": "Big Java, 9th Edition",
                "publishers": ["Wiley"],
            },
        )

        self.assertIn("Requested 10 edition", warning)
        self.assertIn("edition 9", warning)

    def test_select_best_provider_candidate_prefers_exact_edition_match(self) -> None:
        requested_book = build_book_lookup_request(
            {
                "bookname": "Big Java Late Objects",
                "author": "Horstmann",
                "edition": "10th edition",
                "isbn": "",
            }
        )

        selected = select_best_provider_candidate(
            requested_book,
            [
                {
                    "candidate_title": "Big Java Late Objects",
                    "candidate_authors": ["Horstmann"],
                    "candidate_edition_text": "9th edition",
                    "candidate_isbns": [],
                    "provider_book_id": "older",
                },
                {
                    "candidate_title": "Big Java Late Objects",
                    "candidate_authors": ["Horstmann"],
                    "candidate_edition_text": "10th edition",
                    "candidate_isbns": [],
                    "provider_book_id": "exact",
                },
            ],
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected["provider_book_id"], "exact")

    def test_reasonable_provider_match_rejects_different_book(self) -> None:
        requested_book = build_book_lookup_request(
            {
                "bookname": "Big Java Late Objects",
                "author": "Horstmann",
                "edition": "10th edition",
                "isbn": "",
            }
        )
        score_details = score_provider_candidate(
            requested_book=requested_book,
            candidate_title="Java Software Solutions",
            candidate_authors=["Lewis"],
            candidate_edition_text="10th edition",
            candidate_isbns=[],
        )

        self.assertFalse(is_reasonable_provider_match(requested_book, score_details))


if __name__ == "__main__":
    unittest.main()
