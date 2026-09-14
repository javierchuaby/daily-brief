"""Canvas API integration module."""

from .api import (
    CanvasClient,
    extract_announcements_data,
    extract_assignments_data,
    extract_quizzes_data,
    fetch_canvas_data,
)

__all__ = [
    "CanvasClient",
    "fetch_canvas_data",
    "extract_announcements_data",
    "extract_assignments_data",
    "extract_quizzes_data",
]
