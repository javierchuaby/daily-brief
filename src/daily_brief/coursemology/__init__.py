"""Coursemology scraper using the coursemology-py library."""

from .api import (
    CoursemologyClient,
    extract_announcements_data,
    extract_assessments_data,
    extract_categories_data,
    extract_questions_data,
    extract_submissions_data,
    fetch_coursemology_data,
)

__all__ = [
    "CoursemologyClient",
    "fetch_coursemology_data",
    "extract_announcements_data",
    "extract_assessments_data",
    "extract_submissions_data",
    "extract_categories_data",
    "extract_questions_data",
]
