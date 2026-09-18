#!/usr/bin/env python3
"""
Coursemology API integration using the official coursemology-py library.

Fetches data from Coursemology via the official Python client library.
"""

try:
    from coursemology_py import CoursemologyClient
except ImportError:
    CoursemologyClient = None

import logging
from datetime import datetime
from typing import Any, Dict, List

from daily_brief.utils import SGT, parse_sgt_datetime, strip_html_preserve_urls, to_sgt


def _as_sgt(value: Any) -> Any:
    """Normalize a datetime or ISO string to an SGT-aware datetime."""
    if value is None:
        return None
    if isinstance(value, str):
        return parse_sgt_datetime(value)
    return to_sgt(value, SGT)


def fetch_coursemology_data(username: str, password: str, course_id: int = 0) -> str:
    """Fetch data from Coursemology and return Markdown content.

    Args:
        username: NUS email address (e.g., E1406395@u.nus.edu)
        password: NUS account password
        course_id: Coursemology course ID (optional, uses first course if not provided)

    Returns:
        Markdown formatted content with announcements and assessments
    """
    try:
        if CoursemologyClient is None:
            raise RuntimeError(
                "coursemology-py not installed. Install with: "
                "pip install git+https://github.com/rizkiarm/coursemology-py.git"
            )

        client = CoursemologyClient(host="https://coursemology.org")

        # Login
        client.login(username, password)

        # Get courses to find the correct course_id if not provided
        courses = client.courses.index()
        if course_id == 0 and courses.courses:
            course_id = courses.courses[0].id

        # Get course-specific API
        course_api = client.course(course_id)

        # Fetch announcements
        announcements = course_api.announcements.index()

        # Fetch assessments
        assessments = course_api.assessment.assessments.index()

        # Format as Markdown
        header = f"# Coursemology - Course {course_id}\n\n"

        # Announcements section
        announcements_section = "## Announcements\n\n"
        if announcements.announcements:
            for a in announcements.announcements[:5]:
                start_sgt = to_sgt(a.start_time, SGT) if a.start_time else None
                date = (
                    start_sgt.strftime("%Y-%m-%d")
                    if start_sgt
                    else datetime.now(SGT).strftime("%Y-%m-%d")
                )
                announcements_section += f"- **{a.title}** ({date})\n\n"
        else:
            announcements_section += "No announcements found.\n\n"

        # Assessments section
        assessments_section = "## Assessments & Quizzes\n\n"
        if hasattr(assessments, "assessments") and assessments.assessments:
            for a in assessments.assessments[:10]:
                due_date = None
                if a.end_at and hasattr(a.end_at, "effective_time"):
                    sgt_dt = to_sgt(a.end_at.effective_time, SGT)
                    if sgt_dt:
                        due_date = sgt_dt.strftime("%Y-%m-%d")
                elif a.end_at:
                    sgt_dt = to_sgt(a.end_at, SGT)
                    if sgt_dt:
                        due_date = sgt_dt.strftime("%Y-%m-%d")
                assessments_section += (
                    f"- **{a.title}**\n  Due: {due_date or 'No due date'}\n\n"
                )
        else:
            assessments_section += "No assessments found.\n\n"

        return header + announcements_section + assessments_section

    except Exception as e:
        error_msg = f"Error fetching Coursemology data: {e}"
        print(f"   {error_msg}")
        logging.error(error_msg, exc_info=True)
        return "# Coursemology\n\nError fetching data. Check credentials or MFA requirements.\n"


def _get_attr(obj, name, default=None):
    """Get attribute from object or dict."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def extract_announcements_data(announcements: Any) -> List[Dict[str, Any]]:
    """Extract fine-grained announcement data for AI processing.

    Handles both Canvas API dicts and Coursemology Pydantic models.
    """
    data = []
    items = (
        announcements.announcements
        if hasattr(announcements, "announcements")
        else announcements
    )
    for a in items:
        creator_data = None
        creator = _get_attr(a, "creator")
        if creator:
            creator_data = {
                "id": _get_attr(creator, "id"),
                "name": _get_attr(creator, "name"),
            }

        permissions_data = None
        permissions = _get_attr(a, "permissions")
        if permissions:
            permissions_data = {
                "can_edit": _get_attr(permissions, "can_edit"),
                "can_delete": _get_attr(permissions, "can_delete"),
            }

        start_time = _get_attr(a, "start_time")
        end_time = _get_attr(a, "end_time")
        start_time_sgt = _as_sgt(start_time)
        end_time_sgt = _as_sgt(end_time)

        data.append(
            {
                "id": _get_attr(a, "id"),
                "title": _get_attr(a, "title"),
                "content": strip_html_preserve_urls(_get_attr(a, "content")),
                "start_time": start_time_sgt.isoformat() if start_time_sgt else None,
                "end_time": end_time_sgt.isoformat() if end_time_sgt else None,
                "is_unread": _get_attr(a, "is_unread"),
                "is_pinned": _get_attr(a, "is_sticky"),
                "creator": creator_data,
                "permissions": permissions_data,
            }
        )
    return data


def extract_assessments_data(assessments: Any) -> List[Dict[str, Any]]:
    """Extract fine-grained assessment data for AI processing.

    Handles both AssessmentListData (from index) and AssessmentData (from show).
    """
    data = []
    items = (
        assessments.assessments if hasattr(assessments, "assessments") else assessments
    )

    for a in items:
        status = _get_attr(a, "status")
        if status in ["submitted", "graded"]:
            continue

        end_at = _get_attr(a, "end_at")
        due_dt = None
        if end_at:
            if hasattr(end_at, "effective_time") and end_at.effective_time:
                due_dt = end_at.effective_time
            elif hasattr(end_at, "isoformat"):
                due_dt = end_at
        due_date = _as_sgt(due_dt)

        start_at = _get_attr(a, "start_at")
        start_dt = None
        if start_at:
            if hasattr(start_at, "effective_time") and start_at.effective_time:
                start_dt = start_at.effective_time
            elif hasattr(start_at, "isoformat"):
                start_dt = start_at
        start_date = _as_sgt(start_dt)

        # Check if deadline is older than 7 days (ignore start_date for filtering)
        if due_date:
            days_old = (datetime.now(SGT).date() - due_date.date()).days
            if days_old > 7:
                continue

        time_limit = _get_attr(a, "time_limit")

        data.append(
            {
                "id": _get_attr(a, "id"),
                "title": _get_attr(a, "title"),
                "description": strip_html_preserve_urls(_get_attr(a, "description")),
                "start_date": start_date.isoformat() if start_date else None,
                "due_date": due_date.isoformat() if due_date else None,
                "time_limit": time_limit,
                "published": _get_attr(a, "published"),
                "autograded": _get_attr(a, "autograded"),
                "status": status,
                "base_exp": _get_attr(a, "base_exp"),
                "time_bonus_exp": _get_attr(a, "time_bonus_exp"),
            }
        )
    return data


def extract_submissions_data(submissions: Any) -> List[Dict[str, Any]]:
    """Extract fine-grained submission data for AI processing.

    Handles the submissions API response which may be a Pydantic model or raw dict.
    """
    data = []
    items = (
        submissions.submissions if hasattr(submissions, "submissions") else submissions
    )

    for s in items:
        submitted_at_val = _get_attr(s, "submitted_at")
        submitted_at_sgt = _as_sgt(submitted_at_val)
        submitted_at = submitted_at_sgt.isoformat() if submitted_at_sgt else None

        data.append(
            {
                "id": _get_attr(s, "id"),
                "course_user_id": _get_attr(s, "course_user_id"),
                "course_user_name": _get_attr(s, "course_user_name"),
                "assessment_id": _get_attr(s, "assessment_id"),
                "assessment_title": _get_attr(s, "assessment_title"),
                "submitted_at": submitted_at,
                "status": _get_attr(s, "status"),
                "current_grade": _get_attr(s, "current_grade"),
                "max_grade": _get_attr(s, "max_grade"),
                "points_awarded": _get_attr(s, "points_awarded"),
                "is_graded_not_published": _get_attr(s, "is_graded_not_published"),
            }
        )
    return data


def extract_categories_data(categories: Any) -> List[Dict[str, Any]]:
    """Extract fine-grained assessment category data for AI processing."""
    data = []
    items = categories.categories if hasattr(categories, "categories") else categories

    for c in items:
        tabs_data = []
        tabs = _get_attr(c, "tabs")
        if tabs and hasattr(tabs, "categories"):
            for t in tabs.categories:
                tabs_data.append(
                    {
                        "id": _get_attr(t, "id"),
                        "title": _get_attr(t, "title"),
                        "weight": _get_attr(t, "weight"),
                    }
                )

        data.append(
            {
                "id": _get_attr(c, "id"),
                "title": _get_attr(c, "title"),
                "weight": _get_attr(c, "weight"),
                "assessments_count": _get_attr(c, "assessments_count"),
                "tabs": tabs_data,
            }
        )
    return data


def extract_questions_data(questions: Any) -> List[Dict[str, Any]]:
    """Extract fine-grained question data for AI processing.

    Handles question lists from assessments.
    """
    data = []
    items = questions.questions if hasattr(questions, "questions") else questions

    for q in items:
        data.append(
            {
                "id": _get_attr(q, "id"),
                "number": _get_attr(q, "number"),
                "default_title": _get_attr(q, "default_title"),
                "title": _get_attr(q, "title"),
                "type": _get_attr(q, "type"),
                "description": _get_attr(q, "description"),
                "maximum_grade": _get_attr(q, "maximum_grade"),
                "weight": _get_attr(q, "weight"),
                "skill_ids": _get_attr(q, "skill_ids", []),
            }
        )
    return data
