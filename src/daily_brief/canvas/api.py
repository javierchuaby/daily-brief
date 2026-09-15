#!/usr/bin/env python3
"""
Canvas API Integration Module

Provides functions to fetch data from NUS Canvas API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import requests
from requests.exceptions import HTTPError, Timeout

from daily_brief.utils import (
    SGT,
    format_sgt,
    parse_due_date,
    parse_sgt_datetime,
    safe_get_field,
    safe_get_list,
    strip_html_preserve_urls,
    to_sgt,
)


class CanvasClient:
    """Client for interacting with Canvas API."""

    def __init__(self, base_url: str, api_token: str, timeout: int = 30):
        self.base_url = base_url
        self.api_token = api_token
        self.timeout = timeout
        self.headers = {"Authorization": f"Bearer {api_token}"}
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Union[List[Any], Dict[str, Any]]:
        """Make GET request to Canvas API."""
        url = f"{self.base_url}/api/v1{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            # Canvas returns a list for some endpoints
            if isinstance(result, list):
                return result
            return result
        except requests.exceptions.HTTPError:
            if response.status_code == 401:
                raise ValueError(
                    "Invalid Canvas API credentials. Please check your token."
                )
            raise
        except Timeout as e:
            raise ConnectionError(
                f"Canvas API request timed out after {self.timeout} seconds: {e}"
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to connect to Canvas: {e}")

    def get_courses(self) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get list of active courses."""
        return self._get("/courses", {"enrollment_state": "active"})

    def get_announcements(
        self, course_id: int
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get announcements for a course."""
        return self._get("/announcements", {"context_codes[]": f"course_{course_id}"})

    def get_assignments(
        self, course_id: int, include: Optional[List[str]] = None
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get assignments for a course."""
        params = {}
        if include:
            params["include"] = include
        return self._get(f"/courses/{course_id}/assignments", params)

    def get_quizzes(
        self, course_id: int
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get quizzes for a course."""
        try:
            return self._get(f"/courses/{course_id}/quizzes")
        except (ConnectionError, HTTPError):
            # Some courses may not have quizzes endpoint (returns 404)
            return []

    def get_course_progress(
        self, course_id: int
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get course progress for current user."""
        return self._get(f"/courses/{course_id}/course_progress")


def format_announcement(announcement: Dict[str, Any]) -> str:
    """Format announcement as Markdown string."""
    title = announcement.get("title", "No Title")
    message = announcement.get("message", "")[:200]  # Truncate to 200 chars
    posted_at = announcement.get("posted_at", "")

    posted_sgt = parse_sgt_datetime(posted_at)
    date_str = posted_sgt.strftime("%Y-%m-%d") if posted_sgt else posted_at[:10]

    return f"- **{title}** ({date_str})\n  {message[:100]}..."


def format_assignment(assignment: Dict[str, Any]) -> str:
    """Format assignment as Markdown string."""
    title = assignment.get("name", "No Title")
    due_at = assignment.get("due_at", "")
    points = assignment.get("points_possible", "N/A")
    submissions = assignment.get("submissions_count", 0)

    due_date, days_remaining = parse_due_date(due_at)
    if due_date:
        due_str = (
            f"{due_date.strftime('%Y-%m-%d %H:%M')} SGT (in {days_remaining} days)"
        )
    else:
        due_str = "No due date"

    return f"- **{title}**\n  Due: {due_str} | Points: {points} | Submissions: {submissions}"


def format_quiz(quiz: Dict[str, Any]) -> str:
    """Format quiz as Markdown string."""
    title = quiz.get("title", "No Title")
    due_at = quiz.get("due_at", "")
    questions = quiz.get("question_count", "N/A")
    time_limit = quiz.get("time_limit", "N/A")

    due_date, days_remaining = parse_due_date(due_at)
    if due_date:
        due_str = (
            f"{due_date.strftime('%Y-%m-%d %H:%M')} SGT (in {days_remaining} days)"
        )
    else:
        due_str = "No due date"

    return f"- **{title}**\n  Due: {due_str} | Questions: {questions} | Time Limit: {time_limit} min"


def extract_announcements_data(
    announcements: List[Union[Dict[str, Any], Any]],
) -> List[Dict[str, Any]]:
    """Extract fine-grained announcement data for AI processing.

    Handles both Canvas API dicts and Coursemology Pydantic models.
    """
    data = []
    for a in announcements:
        # Handle Canvas-style dict
        if isinstance(a, dict):
            posted_at_str = a.get("posted_at", "")
            posted_dt = parse_sgt_datetime(posted_at_str)
            if posted_dt:
                days_old = (datetime.now(SGT).date() - posted_dt.date()).days
                if days_old > 7:
                    continue

            data.append(
                {
                    "id": a.get("id"),
                    "title": a.get("title", ""),
                    "message": strip_html_preserve_urls(a.get("message", "")),
                    "posted_at": format_sgt(posted_at_str),
                    "is_pinned": a.get("is_pinned", False),
                    "created_at": format_sgt(a.get("created_at", "")),
                    "context_code": a.get("context_code", ""),
                }
            )
        # Handle Coursemology Announcement Pydantic model
        else:
            start_time = getattr(a, "start_time", None)
            if isinstance(start_time, str):
                start_time = parse_sgt_datetime(start_time)
            else:
                start_time = to_sgt(start_time, SGT)

            if start_time:
                days_old = (datetime.now(SGT).date() - start_time.date()).days
                if days_old > 7:
                    continue

            data.append(
                {
                    "id": getattr(a, "id", None),
                    "title": getattr(a, "title", ""),
                    "message": strip_html_preserve_urls(getattr(a, "content", "")),
                    "posted_at": start_time.isoformat() if start_time else None,
                    "is_pinned": getattr(a, "is_sticky", False),
                    "created_at": start_time.isoformat() if start_time else None,
                    "context_code": "",
                }
            )
    return data


def extract_assignments_data(assignments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract fine-grained assignment data for AI processing."""
    data = []
    for a in assignments:
        if a.get("has_submitted_submissions"):
            continue

        due_at = a.get("due_at", "")
        due_date, days_remaining = parse_due_date(due_at)

        # If past due by more than 7 days, filter it out
        if days_remaining is not None and days_remaining < -7:
            continue

        data.append(
            {
                "id": a.get("id"),
                "name": a.get("name", ""),
                "description": strip_html_preserve_urls(a.get("description", "")),
                "due_at": format_sgt(due_at),
                "due_date": due_date.isoformat() if due_date else None,
                "days_remaining": days_remaining,
                "points_possible": safe_get_field(a, "points_possible", 0),
                "grading_type": safe_get_field(a, "grading_type", ""),
                "published": safe_get_field(a, "published", False),
                "submissions_count": safe_get_field(a, "submissions_count", 0),
                "submission_types": safe_get_field(a, "submission_types", []),
                "lock_at": format_sgt(safe_get_field(a, "lock_at", None)),  # type: ignore
                "unlock_at": format_sgt(safe_get_field(a, "unlock_at", None)),  # type: ignore
                "assignment_group_id": safe_get_field(a, "assignment_group_id", None),
            }
        )
    return data


def extract_quizzes_data(quizzes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract fine-grained quiz data for AI processing."""
    data = []
    for q in quizzes:
        if q.get("has_submitted_submissions"):
            continue

        due_at = q.get("due_at", "")
        due_date, days_remaining = parse_due_date(due_at)

        if days_remaining is not None and days_remaining < -7:
            continue

        data.append(
            {
                "id": q.get("id"),
                "title": q.get("title", ""),
                "description": strip_html_preserve_urls(q.get("description", "")),
                "due_at": format_sgt(due_at),
                "due_date": due_date.isoformat() if due_date else None,
                "days_remaining": days_remaining,
                "question_count": safe_get_field(q, "question_count", 0),
                "time_limit": safe_get_field(q, "time_limit", 0),
                "allowed_attempts": safe_get_field(q, "allowed_attempts", 1),
                "quiz_type": safe_get_field(q, "quiz_type", ""),
                "published": safe_get_field(q, "published", False),
                "lock_at": format_sgt(safe_get_field(q, "lock_at", None)),  # type: ignore
                "unlock_at": format_sgt(safe_get_field(q, "unlock_at", None)),  # type: ignore
            }
        )
    return data


def generate_course_markdown(
    course_id: int, course_code: str, client: CanvasClient
) -> str:
    """Generate Markdown content for a Canvas course."""
    header = f"# {course_code}\n\n"

    # Get announcements
    announcements = client.get_announcements(course_id)
    announcements_section = "## Announcements\n\n"
    announcements_list = safe_get_list(announcements, "announcements")
    if announcements_list:
        for a in announcements_list[:5]:  # Top 5
            announcements_section += format_announcement(a) + "\n\n"
    else:
        announcements_section += "No announcements found.\n\n"

    # Get assignments
    assignments = client.get_assignments(course_id, ["assignment_overrides"])
    assignments_section = "## Assignments\n\n"
    assignments_list = safe_get_list(assignments, "assignments")
    if assignments_list:
        # Filter upcoming assignments (SGT now matches SGT-converted due dates)
        today = datetime.now(SGT)
        upcoming = [
            a
            for a in assignments_list
            if isinstance(a, dict)
            and a.get("due_at")
            and (due := parse_due_date(a["due_at"])[0]) is not None
            and due > today
        ]
        upcoming = sorted(upcoming, key=lambda x: x.get("due_at", ""))[:5]  # Top 5

        for a in upcoming:
            assignments_section += format_assignment(a) + "\n\n"
    else:
        assignments_section += "No assignments found.\n\n"

    # Get quizzes
    quizzes = client.get_quizzes(course_id)
    quizzes_section = "## Quizzes\n\n"
    quizzes_list = safe_get_list(quizzes, "quizzes")
    if quizzes_list:
        # Filter upcoming quizzes (SGT now matches SGT-converted due dates)
        today = datetime.now(SGT)
        upcoming = [
            q
            for q in quizzes_list
            if isinstance(q, dict)
            and q.get("due_at")
            and (due := parse_due_date(q["due_at"])[0]) is not None
            and due > today
        ]
        upcoming = sorted(upcoming, key=lambda x: x.get("due_at", ""))[:5]  # Top 5

        for q in upcoming:
            quizzes_section += format_quiz(q) + "\n\n"
    else:
        quizzes_section += "No quizzes found.\n\n"

    return header + announcements_section + assignments_section + quizzes_section


def fetch_canvas_data(
    api_token: str, base_url: str, courses: Dict[str, int]
) -> Dict[str, str]:
    """Fetch data from Canvas for multiple courses.

    Args:
        api_token: Canvas API token
        base_url: Canvas base URL
        courses: Dict mapping course_code to course_id

    Returns:
        Dict mapping course_code to Markdown content
    """
    client = CanvasClient(base_url, api_token)
    result: Dict[str, str] = {}

    for course_code, course_id in courses.items():
        try:
            print(f"   Fetching {course_code} (ID: {course_id})...")
            content = generate_course_markdown(course_id, course_code, client)
            result[course_code] = content
        except ValueError as e:
            print(f"   ✗ Invalid Canvas credentials: {e}")
        except ConnectionError as e:
            print(f"   ✗ Failed to connect to Canvas: {e}")
        except HTTPError as e:
            # Some endpoints may return 404 (e.g., quizzes for courses without quizzes)
            if e.response is not None and e.response.status_code == 404:
                print(
                    f"   ⚠  {course_code} - Some endpoints not available (404), generating partial data"
                )
                content = generate_course_markdown(course_id, course_code, client)
                result[course_code] = content
            elif e.response is not None:
                print(
                    f"   ✗ Failed to fetch {course_code}: HTTP {e.response.status_code}"
                )
                result[course_code] = (
                    f"# {course_code}\n\nError fetching data: HTTP {e.response.status_code}\n"
                )
            else:
                print(
                    f"   ✗ Failed to fetch {course_code}: HTTP error without response"
                )
                result[course_code] = (
                    f"# {course_code}\n\nError fetching data: HTTP error without response\n"
                )
        except Exception as e:
            print(f"   ✗ Failed to fetch {course_code}: {e}")
            result[course_code] = f"# {course_code}\n\nError fetching data: {e}\n"

    return result
